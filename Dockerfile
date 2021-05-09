FROM ubuntu:18.04
MAINTAINER mipu94
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && \
    apt-get install -y wget \
    cmake \
    bison \
    git \
    unzip \
    xz-utils \
    apache2 \
    llvm-7 \ 
    clang-7 \
    libclang-7-dev \
    tzdata \
    sed \ 
    ruby

WORKDIR /root/

# install ninja
RUN wget https://github.com/ninja-build/ninja/releases/download/v1.10.0/ninja-linux.zip \
 && unzip ninja-linux.zip \
 && mv ninja /usr/local/bin/ \
 && rm ninja-linux.zip

# install clang
RUN wget https://prereleases.llvm.org/10.0.0/rc3/clang+llvm-10.0.0-rc3-x86_64-linux-gnu-ubuntu-18.04.tar.xz \
 && tar xvf clang+llvm-10.0.0-rc3-x86_64-linux-gnu-ubuntu-18.04.tar.xz \
 && mv clang+llvm-10.0.0-rc3-x86_64-linux-gnu-ubuntu-18.04 clang

ARG WEBKIT_VERSION
RUN  apt-get update --fix-missing
# download webkit
RUN wget https://webkitgtk.org/releases/webkitgtk-${WEBKIT_VERSION}.tar.xz && \
    tar xvf webkitgtk-${WEBKIT_VERSION}.tar.xz && \
    cd webkitgtk-${WEBKIT_VERSION} && \
    printf 'y\n' | ./Tools/gtk/install-dependencies 

ARG FUZZ_TYPE
ADD patches /patches

RUN patch -s -p0 < /patches/patch-${WEBKIT_VERSION}.diff

WORKDIR /root/webkitgtk-${WEBKIT_VERSION}
# patch asan build
#address, memory
ENV ASAN_TYPE=address  
RUN sed -i 's~COMMAND CC=${CMAKE_C_COMPILER} CFLAGS=-Wno-deprecated-declarations LDFLAGS=~COMMAND CC=${CMAKE_C_COMPILER} CFLAGS=\\\"-Wno-deprecated-declarations -fsanitize=address\\\" LDFLAGS=\\\"-fsanitize=address\\\"~g' Source/WebKit/PlatformGTK.cmake

RUN sed -i 's~COMMAND CC=${CMAKE_C_COMPILER} CFLAGS=-Wno-deprecated-declarations~COMMAND CC=${CMAKE_C_COMPILER} CFLAGS=\\\"-Wno-deprecated-declarations -fsanitize=address\\\"~g' Source/WebKit/PlatformGTK.cmake

RUN sed -i 's~LDFLAGS="${INTROSPECTION_ADDITIONAL_LDFLAGS}"~LDFLAGS=\\\"${INTROSPECTION_ADDITIONAL_LDFLAGS} -fsanitize=address\\\"~g' Source/WebKit/PlatformGTK.cmake

ENV CC="$BUILD_PATH/clang/bin/clang" \
      CXX="$BUILD_PATH/clang/bin/clang++" \
      CFLAGS="-fsanitize=$ASAN_TYPE" \
      CXXFLAGS="-fsanitize=$ASAN_TYPE" \
      LDFLAGS="-fsanitize=$ASAN_TYPE" \
      ASAN_OPTIONS="detect_leaks=0"
RUN mkdir mybuild && cd mybuild && cmake \
      -DCMAKE_BUILD_TYPE=Release  \
      -DCMAKE_INSTALL_PREFIX=/usr \
      -DCMAKE_SKIP_RPATH=ON       \
      -DPORT=GTK                  \
      -DLIB_INSTALL_DIR=/usr/lib  \
      -DUSE_LIBHYPHEN=OFF         \
      -DENABLE_MINIBROWSER=ON     \
      -DUSE_WOFF2=OFF             \
      -DUSE_WPE_RENDERER=OFF      \
      -DENABLE_BUBBLEWRAP_SANDBOX=OFF \
-Wno-dev -G Ninja -DCMAKE_C_COMPILER="/root/clang/bin/clang" -DCMAKE_CXX_COMPILER="/root/clang/bin/clang++" .. && ninja && ninja install

RUN cp -rf mybuild /root/webkitASAN

RUN echo "export DISPLAY=:0" >> ~/.bashrc

ADD resource/ /resource
RUN mv /resource/favocado/Generator /var/www/html

RUN echo "python /resource/monitor.py $FUZZ_TYPE 20 >/root/logfuzzing" >>/resource/run.sh 

WORKDIR /root
RUN rm clang+*  webkitgtk-* -rf

CMD ["/resource/run.sh"]

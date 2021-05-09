#!/bin/bash
cd resource
git clone https://github.com/favocado/pre-release-favocado
mv pre-release-favocado favocado
cd favocado
git checkout -f webkit-gtk
cd ../..
WEBKIT_VERSION=2.28.3
FUZZ_TYPE="context-dependent"
# FUZZ_TYPE="non-context"
SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
CORPUS="$SCRIPTPATH/corpus"
mkdir -p crashes/webkit${WEBKIT_VERSION}
mkdir corpus

docker build . -t webkit_asan${WEBKIT_VERSION} --build-arg WEBKIT_VERSION=${WEBKIT_VERSION} --build-arg FUZZ_TYPE=${FUZZ_TYPE}

for ((i = 0 ; i <= 8 ; i++)); do
	docker run -it --cpus="2.0" --memory="2g"  -d -v $SCRIPTPATH/crashes/webkit${WEBKIT_VERSION}:/root/crashes -v $SCRIPTPATH/corpus:/root/corpus  --name="fuzzwebkit$i" webkit_asan${WEBKIT_VERSION} /bin/bash -c /resource/run.sh
done

if [ $FUZZ_TYPE == "context-free" ]
	then
		while true
		do
			if [ $(ls ./corpus| wc -l) -le 50 ]
				then
					find $CORPUS -name '*.html' | head -n 50 | xargs -I {} mv {} corpus;
					echo " moved 50 new files";
					sleep 20;
			fi
			sleep 20;
		done
fi
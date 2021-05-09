import os
import subprocess, signal
import time
import re
import urllib
import glob
import string
import random
import sys
import shutil


# python monitor in-context 10
FuzzType = sys.argv[1]
timeout = int(sys.argv[2])


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

Cpath = os.path.dirname(os.path.abspath(__file__))
homepath = "/root"
CorpusPath = homepath + "/corpus"
CrashPath = homepath + "/crashes"
log_path = homepath + "/fuzzinglog/"
logfile = log_path + "/log.html"
asanlog = log_path + "/asan.txt"


global F_pid
F_pid = -1

# initialize logging folder to fuzz.
def initFuzz():
    if not os.path.isdir(log_path):
        os.mkdir(log_path)
    else: 
        print "folder Existing "
        sys.stdout.flush()
    subprocess.Popen(['chmod', '777', log_path], stdout=subprocess.PIPE)
    print "created log_path :",log_path
    sys.stdout.flush()
    subprocess.call("rm -rf /root/.cache /root/.local",shell=True)
    

# kill all process match name
def kill(name):
    p = subprocess.Popen(['ps', '-ef'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    for line in out.splitlines():
        if name in line:
            if name == line.split(None, 4)[2]:
                pid = line.split(None, 4)[1]
                print "killing",pid
                sys.stdout.flush()
                p = subprocess.Popen(['kill', '-9',str(pid) ], stdout=subprocess.PIPE)
                p.wait()
                time.sleep(1)
                return

# fix testcase if it's wrong.
def correctCorpus(file):
    print file
    f = open(file,"rb")
    contents = f.readlines()
    if len(contents) == 0:
        return
    f.close()
    # auto append </script> to last line if not found.
    if "</script>" not in contents[-1]:
        f = open(file, "ab")
        f.write("confirm('ran all')")
        f.write("</script>")
        f.close()

def startVirtualDisplayer():
    print "restarting virtualdisplayer"
    p = subprocess.Popen(["rm /tmp/.X1337-lock"],shell=True, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(0.2)
    cmd = "Xvfb :1337 -screen 0 1920x1080x24"
    subprocess.Popen([cmd],shell=True, stdout=subprocess.PIPE)
    time.sleep(0.2)


def get_crash_address():
    list = os.listdir(log_path)
    af= ""
    for filename in list:
        if filename[0] == ".":
            af =    log_path+"/"+filename   
            with open(log_path+"/"+filename) as f:
                lines = f.readlines()
                for line in lines:
                    if "#0 0x" in line:
                        return line.split(")")[-2].split("/")[-1]
    print open(af,"rb").read()
    return "HAHA"


def get_crash():
    print "checking crash"
    sys.stdout.flush()
    global F_pid
    # waiting for writting ASAN log to file
    time.sleep(2)
    # check duplicate pattern
    for filename in os.listdir(log_path):
        if filename[0] == ".":
           with open(log_path+"/"+filename) as f:
                data = f.read() 
                duplicate_pattern_file = CrashPath+"/duplicate"
                if os.path.isfile(duplicate_pattern_file):
                    dup_pattern = open(duplicate_pattern_file, "rb").readlines()
                    for pattern in dup_pattern:
                        if len(pattern) < 2:
                            continue
                        if pattern.strip('\x0a').strip("\x0d") in data:
                            print "=====> Duplicated to ", pattern
                            sys.stdout.flush()
                            p = subprocess.Popen(["rm -rf %s"%log_path],shell=True, stdout=subprocess.PIPE)
                            p.wait()
                            kill(str(F_pid))
                            return

    # interesting crash -> save
    print "getting crash"
    EIP = get_crash_address()
    if EIP != "":    
        crashfolder = CrashPath + "/" + EIP
        if not os.path.isdir(crashfolder):
            os.mkdir(crashfolder)
        fuzz_id = randomString()
        new_path = crashfolder + "/" + fuzz_id

        print "moving crashlog from %s to %s"%(log_path, new_path)
        sys.stdout.flush()
        time.sleep(1)
        p = subprocess.Popen(["mv %s %s"%(log_path,new_path)],shell=True, stdout=subprocess.PIPE)
        p.wait()
        print "====>MOVED"
    else:
        print "not found EIP??"

    kill(str(F_pid))
    return

def checkTimeOut():
    f = open(logfile, "rb")
    data = f.read()
    if "ran all" in data:
        print "ran all!"
        time.sleep(1)
        return True
    if not os.path.exists(logfile):
        print "no log file!"
        return False
    changeTime = os.path.getmtime(logfile)
    if time.time() - changeTime > timeout:
        print "timeout!"
        return True
    else:
        return False

def run(url):
    global F_pid
    f = open(logfile,"wb")
    f.close()
    cmd = "DISPLAY=:1337 ASAN_OPTIONS=allocator_may_return_null=1,detect_leaks=0,exitcode=42,log_path=%s  LD_LIBRARY_PATH=/root/webkitASAN/lib ASAN_SYMBOLIZER_PATH=/root/clang/bin/llvm-symbolizer /root/webkitASAN/bin/MiniBrowser %s 2>%s"%(log_path,url,asanlog)

    display = False
    while display == False:
        p = subprocess.Popen([cmd],shell=True, stdout=subprocess.PIPE)
        F_pid = p.pid 
        time.sleep(2)
        data = open(asanlog, "rb").read()
        if "cannot open display:" not in data:
            display = True
        else:
            display = False
            kill(str(F_pid))
            startVirtualDisplayer()



def get_random_sample(corpus):
    files =os.listdir(corpus) 
    cfile = os.path.join(corpus, random.choice(files))
    newfile = os.path.join(log_path, "test.html")
    p = subprocess.Popen(["mv %s %s"%( cfile, newfile )],shell=True, stdout=subprocess.PIPE)
    p.wait()
    if(os.path.exists(newfile)):
        return newfile
    else:
        print "testcase not found: ", newfile
        return ""
    return ""
        
def find_string(folder, string):
	for ifile in os.listdir(folder):
		with open( os.path.join(folder, ifile)) as f:
			contents = f.read()
			if string in contents:
				return True
	return False

# asan log file should be .6123 .1234 .4321
def checkAsanLog():
	list = os.listdir(log_path)
	for filename in list:
		if filename[0] == ".":
			return True
	return False

def Fuzz():
    initFuzz()
    global F_pid
    if FuzzType == "context-free":
        if not os.path.isdir(CorpusPath):
            print "context-free without copus?"
        working_file = get_random_sample(CorpusPath)
        if working_file == "":
            print "no more testcase"
            time.sleep(10)
            return
        correctCorpus(working_file)
        run(working_file)
    else: # FuzzType == "context-dependent"
        p = subprocess.Popen(["service apache2 start"],shell=True, stdout=subprocess.PIPE)
        p.wait()
        run("http://127.0.0.1/Generator/Run/fuzz.html")
        
    while 1:
        time.sleep(3)
        #crash -> add confirmed folder 
        if checkAsanLog():
            get_crash()
            return

        if checkTimeOut():
            if checkAsanLog():
                get_crash()
            sys.stdout.flush()
            time.sleep(1)
            p = subprocess.Popen(["rm -rf %s"%log_path],shell=True, stdout=subprocess.PIPE)
            p.wait()
            kill(str(F_pid))
            print "DONE!"
            sys.stdout.flush()
            return


# for i in range(10):
while(1):
    Fuzz()


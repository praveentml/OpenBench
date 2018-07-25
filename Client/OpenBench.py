from __future__ import print_function

import ast, argparse, time, sys, platform, multiprocessing, hashlib
import shutil, subprocess, requests, zipfile, os, math, json


## Configuration
HTTP_TIMEOUT   = 30  # Timeout in seconds for web requests
GAMES_PER_TASK = 250 # Total games to complete for each workload
REPORT_RATE    = 10  # Games per upload. Must divide GAMES_PER_TASK

# Run from any location ...
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Argument Parsing ... <Username> <Password> <Server> <Threads>
parser = argparse.ArgumentParser()
parser.add_argument('-U', '--username', help='Username', required=True)
parser.add_argument('-P', '--password', help='Password', required=True)
parser.add_argument('-S', '--server', help='Server Address', required=True)
parser.add_argument('-T', '--threads', help='# of Threads', required=True)
arguments = parser.parse_args()

# Client Parameters
USERNAME = arguments.username
PASSWORD = arguments.password
SERVER   = arguments.server
THREADS  = int(arguments.threads)

# Windows treated seperatly from Linux
IS_WINDOWS = platform.system() == 'Windows'

# Server wants to identify different machines
OS_NAME = platform.system() + ' ' + platform.release()

# Solution taken from Fishtest
def killProcess(process):
    try:
        # process.kill doesn't kill subprocesses on Windows
        if IS_WINDOWS: subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else: process.kill()
        process.wait()
        process.stdout.close()
    except:
        pass

def getNameAsExe(program):
    if IS_WINDOWS: return program + '.exe'
    return program

def getExecutable(program):
    executable = 'Engines/' + getNameAsExe(program)
    if os.path.isfile(executable):
        return executable
    return getBashLocation(program) + getBashFile(program)

def getExecutableLocation(program):
    executable = getNameAsExe(program)
    directory = 'Engines/'
    if os.path.isfile(directory + executable):
        return directory
    return getBashLocation(program)
	
def getExecutableFile(program):
    executable = getNameAsExe(program)
    if os.path.isfile('Engines/' + executable):
        return executable
    return getBashFile(program)

def getNameAsZip(program):
    return program + '.zip'

def getBashLocation(program):
    return 'Engines/' + program + '/bin/'

def getBashFile(program):
    if IS_WINDOWS: return program + '.bat'
    return program

def getFile(source, outname):
    # Read a file from the given source and save it locally
    print('Downloading : {0}'.format(source))
    request = requests.get(url=source, stream=True, timeout=HTTP_TIMEOUT)
    with open(outname, 'wb') as fout:
        for chunk in request.iter_content(chunk_size=1024):
            if chunk: fout.write(chunk)
        fout.flush()

def getCoreFiles():

    # Ask the server where the core files are saved
    request = requests.get(SERVER + '/getFiles/', timeout=HTTP_TIMEOUT)
    location = request.content.decode('utf-8')

    # Download the proper cutechess program, and a dll if needed
    if IS_WINDOWS:
        if not os.path.isfile('cutechess.exe'):
            getFile(location + 'cutechess-windows.exe', 'cutechess.exe')
        if not os.path.isfile('Qt5Core.dll'):
            getFile(location +'cutechess-qt5core.dll', 'Qt5Core.dll')
    else:
        if not os.path.isfile('cutechess'):
            getFile(location + 'cutechess-linux', 'cutechess')
            os.system('chmod 777 cutechess')
        if not os.path.isfile('libcutechess.so.1'):
            getFile(location + 'libcutechess.so.1', 'libcutechess.so.1')

def getEngine(data):

    name      = data['sha']
    source    = data['source']
    exeFile   = getExecutableFile(name)
    exe       = getExecutable(name)
    unzipname = source.split('/')[-3] + '-' + source.split('/')[-1].replace('.zip', '')

    # Don't redownload an engine we already have
    if os.path.isfile(exe):
        print('Found executable file')
        return
		
    # Log the fact that we are setting up a new engine
    print('\nSETTING UP ENGINE')
    print('Engine      :', data['name'])
    print('Commit      :', data['sha'])
    print('Source      :', source)
    print('unzipname   :', unzipname)

    # Extract and delete the zip file
    getFile(source, name + '.zip')
    print('Extracting zip')
    with zipfile.ZipFile(name + '.zip') as data:
        data.extractall('tmp')
    os.remove(name + '.zip')
    os.rename('tmp/{0}'.format(unzipname), 'tmp/{0}'.format(name))

    print('Starting build')
    # Build Engine using provided gcc and PGO flags
    subprocess.Popen(
        ['gradlew', 'build'],
        cwd='tmp/{0}/'.format(name),
		shell=True).wait()

    # Create the Engines directory if it does not exist
    if not os.path.isdir('Engines'):
        os.mkdir('Engines')

    print('Moving files')
    # Move the compiled engine
    if os.path.isfile('tmp/{0}/src/{1}'.format(name, exeFile)):
        os.rename('tmp/{0}/src/{1}'.format(name, exeFile), exe)

    elif os.path.isfile('tmp/{0}/src/{1}'.format(name, name)):
        os.rename('tmp/{0}/src/{1}'.format(name, name), exe)
		
    if os.path.isfile('tmp/{0}/build/distributions/{1}.zip'.format(name, name)):
        with zipfile.ZipFile(name + '.zip') as data:
            data.extractall('tmp/{0}/build/distributions/{1}'.format(name, name))
        shutil.move('tmp/{0}/build/distributions/{1}/{2}'.format(name, name, name), 'Engines/{0}'.format(name))

    print('Cleaning up')
    # Cleanup the unzipped zip file
    shutil.rmtree('tmp')

def getCutechessCommand(data, scalefactor):

    if IS_WINDOWS: exe = 'cutechess.exe'
    else:          exe = './cutechess'

    timecontrol = data['test']['timecontrol']

    # Parse X / Y + Z time controls
    if '/' in timecontrol and '+' in timecontrol:
        moves = timecontrol.split('/')[0]
        start, inc = map(float, timecontrol.split('/')[1].split('+'))
        start = round(start * scalefactor, 2)
        inc = round(inc * scalefactor, 2)
        timecontrol  = moves + '/' + str(start) + '+' + str(inc)

    # Parse X / Y time controls
    elif '/' in timecontrol:
        moves = timecontrol.split('/')[0]
        start = float(timecontrol.split('/')[1])
        start = round(start * scalefactor, 2)
        timecontrol = moves + '/' + str(start)

    # Parse X + Z time controls
    else:
        start, inc = map(float, timecontrol.split('+'))
        start = round(start * scalefactor, 2)
        inc = round(inc * scalefactor, 2)
        timecontrol = str(start) + '+' + str(inc)

    # Find Threads / Options for the Dev Engine
    tokens = data['test']['dev']['options'].split(' ')
    devthreads = int(tokens[0].split('=')[1])
    devoptions = ' option.'.join(['']+tokens)

    # Find Threads / Options for the Base Engine
    tokens = data['test']['base']['options'].split(' ')
    basethreads = int(tokens[0].split('=')[1])
    baseoptions = ' option.'.join(['']+tokens)

    # Finally, output the time control for the user
    print ('ORIGINAL  :', data['test']['timecontrol'])
    print ('SCALED    :', timecontrol)
    print ('')
	
    devExecutable = getExecutableFile(data['test']['dev']['sha'])
    devLocation = getExecutableLocation(data['test']['dev']['sha'])
	
    baseExecutable = getExecutableFile(data['test']['base']['sha'])
    baseLocation = getExecutableLocation(data['test']['base']['sha'])

    generalFlags = (
        '-repeat'
        ' -srand ' + str(int(time.time())) +
        ' -resign movecount=3 score=400'
        ' -draw movenumber=40 movecount=8 score=10'
        ' -concurrency ' + str(int(math.floor(THREADS / max(devthreads, basethreads)))) +
        ' -games ' + str(GAMES_PER_TASK) +
        ' -recover'
        ' -wait 10'
    )

    devflags = (
        '-engine'
        ' stderr=err1.txt ' +
        ' cmd=./' + devLocation + devExecutable +
        ' proto=' + data['test']['dev']['protocol'] +
        ' tc=' + timecontrol + devoptions
    )

    baseflags = (
        '-engine' +
        ' stderr=err2.txt ' +
        ' cmd=./' + baseLocation + baseExecutable +
        ' proto=' + data['test']['base']['protocol'] +
        ' tc=' + timecontrol + baseoptions
    )

    bookflags = (
        '-openings'
        ' file=' + data['test']['book']['name'] +
        ' format=pgn'
        ' order=random'
        ' plies=16'
    )

    return ' '.join([exe, generalFlags, devflags, baseflags, bookflags])

def singleCoreBench(name, outqueue):

    try:
        # Format file path because of Windows ...
        directory = getExecutableLocation(name)
        executable = getExecutableFile(name)

        # Run bench from CMD, pipe stderr into stdout
        data, empty = subprocess.Popen(
            '{0} bench'.format(executable).split(),
            cwd=directory,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).communicate()

        # Split line by line after decoding
        data = data.decode('ascii').strip().split('\n')

        # Parse and dump results into queue
        bench = int(data[-2].split(':')[1])
        nps   = int(data[-1].split(':')[1])
        outqueue.put((bench, nps))

    # Bad compile or bad output, force an error
    except: outqueue.put((0, 0))

def getBenchSignature(engine):

    print ('\nRunning Benchmark for {0} on {1} cores'.format(engine['name'], THREADS))

    # Allow each process to send back completition times
    outqueue = multiprocessing.Queue()

    # Launch and wait for completion of one process for each core
    processes = []
    for f in range(THREADS):
        processes.append(
            multiprocessing.Process(
                target=singleCoreBench,
                args=(engine['sha'], outqueue,)))
    for p in processes: p.start()
    for p in processes: p.join()

    # Parse data and compute average speed
    data  = [outqueue.get() for f in range(THREADS)]
    bench = [f[0] for f in data]
    nps   = [f[1] for f in data]
    avg   = sum(nps) / len(nps)

    # All benches should be the same
    if (len(set(bench)) > 1):
        return (0, 0)

    # Log and return computed bench and speed
    print ('Bench for {0} is {1}'.format(engine['name'], bench[0]))
    print ('NPS   for {0} is {1}'.format(engine['name'], int(avg)))
    return (bench[0], avg)

def reportWrongBench(data, engine):

    # Server wants verification for reporting wrong benchs
    postdata = {
        'username'  : USERNAME,
        'password'  : PASSWORD,
        'engineid'  : engine['id'],
        'testid'    : data['test']['id']}
    return requests.post('{0}/wrongBench/'.format(SERVER), data=postdata, timeout=HTTP_TIMEOUT).text

def reportNPS(data, nps):

    # Server wants verification for reporting nps counts
    try:
        postdata = {
            'nps'       : nps,
            'username'  : USERNAME,
            'password'  : PASSWORD,
            'machineid' : data['machine']['id']}
        return requests.post('{0}/submitNPS/'.format(SERVER), data=postdata, timeout=HTTP_TIMEOUT).text
    except: print ('<Warning> Unable to reach server')

def reportResults(data, wins, losses, draws, crashes, timeloss):

    # Server wants verification for reporting nps counts
    try:
        postdata = {
            'wins'      : wins,
            'losses'    : losses,
            'draws'     : draws,
            'crashes'   : crashes,
            'timeloss'  : timeloss,
            'username'  : USERNAME,
            'password'  : PASSWORD,
            'machineid' : data['machine']['id'],
            'resultid'  : data['result']['id'],
            'testid'    : data['test']['id']}
        return requests.post('{0}/submitResults/'.format(SERVER), data=postdata, timeout=HTTP_TIMEOUT).text
    except:
        print ('<Warning> Unable to reach server')
        return "Unable"


def completeWorkload(data):

    # Download and verify bench of dev engine
    getEngine(data['test']['dev'])
    devbench, devnps = getBenchSignature(data['test']['dev'])
    if devbench != int(data['test']['dev']['bench']):
        print ('<ERROR> Invalid Bench. Got {0} Expected {1}'.format(
            devbench, int(data['test']['dev']['bench'])))
        reportWrongBench(data, data['test']['dev'])
        return

    # Download and verify bench of base engine
    getEngine(data['test']['base'])
    basebench, basenps = getBenchSignature(data['test']['base'])
    if basebench != int(data['test']['base']['bench']):
        print ('<ERROR> Invalid Bench. Got {0} Expected {1}'.format(
            basebench, int(data['test']['base']['bench'])))
        reportWrongBench(data, data['test']['base'])
        return

    # Download and verify sha of the opening book
    print('\nVERIFYING OPENING BOOK')
    if not os.path.isfile(data['test']['book']['name']):
        getFile(data['test']['book']['source'], data['test']['book']['name'])
    with open(data['test']['book']['name']) as fin:
        digest = hashlib.sha256(fin.read().encode('utf-8')).hexdigest()
    print ('Correct SHA : {0}'.format(digest.upper()))
    print ('MY Book SHA : {0}'.format(data['test']['book']['sha'].upper()))
    if (digest != data['test']['book']['sha']):
        print ('<ERROR> Invalid SHA for {0}'.format(data['test']['book']['name']))
        sys.exit()

    # Compute and report CPU scaling factor
    avgnps = (devnps + basenps) / 2.0
    reportNPS(data, avgnps)
    scalefactor = int(data['test']['nps']) / avgnps
    print ('\nFACTOR    : {0}'.format(round(1 / scalefactor, 2)))

    # Compute and report cutechess-cli string
    command = getCutechessCommand(data, scalefactor)
    print(command)

    # Spawn cutechess process
    process = subprocess.Popen(
        command.split(),
        stdout=subprocess.PIPE
    )

    # Tracking results of each game
    crashes = timeloss = 0
    sent = [0, 0, 0]; score = [0, 0, 0]

    while True:

        # Grab the next line of cutechess output
        line = process.stdout.readline().strip().decode('ascii')
        if line != '': print(line)

        # Update the current score line
        if line.startswith('Score of'):
            chunks = line.split(':')
            chunks = chunks[1].split()
            score = list(map(int, chunks[0:5:2]))

        # Search for the end of the cutechess process
        if line.startswith('Finished match') or 'Elo difference' in line:
            killProcess(process)
            break

        # Parse engine crashes
        if 'disconnects' in line or 'connection stalls' in line:
            crashes += 1

        # Parse losses on time
        if 'on time' in line:
            timeloss += 1

        # Report back results in batches
        if line.startswith('Score of') and (sum(score) - sum(sent)) % REPORT_RATE == 0:

            # Compute scoreline differences
            wins   = score[0] - sent[0]
            losses = score[1] - sent[1]
            draws  = score[2] - sent[2]

            # Send results to server
            status = reportResults(data, wins, losses, draws, crashes, timeloss)

            # Task ended, deleted, ..., exit back for new task
            if status == "Stop":
                killProcess(process)
                break

            # Only reset tracking when the server was reached
            if status != "Unable":
                crashes = timeloss = 0
                sent = score[::]

if __name__ == '__main__':

    # Machine ID numbers are tracked by the server, and saved locally
    try:
        with open('machine.txt') as fin:
            machineid = fin.readlines()[0]
    except:
        machineid = 'None'
        print('<Warning> Machine unregistered, will register with Server')

    # Download cutechess and any .dlls needed
    getCoreFiles()

    # Each Workload request will send this data
    postdata = {
        'username'  : USERNAME,
        'password'  : PASSWORD,
        'threads'   : THREADS,
        'osname'    : OS_NAME,
        'machineid' : machineid,
    }

    while True:

        try:
            # Request the information for the next workload
            request = requests.post('{0}/getWorkload/'.format(SERVER), data=postdata, timeout=HTTP_TIMEOUT)

            # Response is a dictionary of information, 'None', or an error string
            data = request.content.decode('utf-8')

            # Server has nothing to run, ask again later
            if data == 'None':
                print ('<Warning> Server has no workloads for us')
                time.sleep(60)
                continue

            # Server was unable to authenticate us
            if data == 'Bad Credentials':
                print ('<ERROR> Invalid Login Credentials')
                sys.exit()

            # Server might reject our Machine ID, in which case
            # we register again, but without an ID number. Server
            # will send us a new ID, and we can save that locally
            if data == 'Bad Machine':
                print ('<ERROR> Bad Machine, Registering again')
                postdata['machineid'] = 'None'
                continue

            # Convert response into a data dictionary
            data = ast.literal_eval(data)

            # Update and save our assigned machine ID
            postdata['machineid'] = data['machine']['id']
            with open('machine.txt', 'w') as fout:
                fout.write(str(postdata['machineid']))

            # Begin working on the games to be played
            completeWorkload(data)

        except Exception as error:
            print ('<ERROR> {0}'.format(str(error)))
            time.sleep(10)

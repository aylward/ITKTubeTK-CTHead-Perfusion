import argparse
import subprocess
import sys
import json
import time
import csv
import traceback
from os import path
import win32file, win32pipe, pywintypes, winerror

from common import WinPipeSock, Message, EXIT_FAILURE, PIPE_NAME, LOCK_FILE, LOG_FILE, EXIT_SUCCESS

class Retry(Exception):
    pass

def prepare_argparser():
    parser = argparse.ArgumentParser(description='ARGUS inference')
    parser.add_argument('video_file', help='video file to analyze.')
    parser.add_argument('--debug', action='store_true',
                        help='output debugging info. '
                             'Debug info will appear in the output CSV, '
                             'as well as the "<video_filename>-debug-output" folder.')
    return parser

def start_service():
    subprocess.run(['sc.exe', 'start', 'ARGUS'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def formatHHMMSS(secs=None):
    if secs is None:
        secs = time.time()
    msecs = int(1000 * (secs - int(secs)))
    return f'{time.strftime("%H:%M:%S", time.gmtime(secs))}:{msecs}'

def dbg(*args, **kwargs):
    print(f'DEBUG [{formatHHMMSS()}]:', *args, **kwargs)

def write_result(video_file, result, debug=False):
    stats = result['stats']
    timers = stats['timers']
    ptx_detected = 'No' if result['sliding'] else 'Yes'

    result_filename = path.join(
        path.dirname(path.abspath(video_file)),
        f'{path.splitext(path.basename(video_file))[0]}.csv'
    )
    csv_data = dict(
        filename=result_filename,
        PTX_detected=ptx_detected,
        start_read_video=formatHHMMSS(timers['Read Video']['start']),
        end_read_video=formatHHMMSS(timers['Read Video']['end']),
        elapsed_read_video=round(timers['Read Video']['elapsed'], 3),
        start_process_video=formatHHMMSS(timers['Process Video']['start']),
        end_process_video=formatHHMMSS(timers['Process Video']['end']),
        elapsed_process_video=round(timers['Process Video']['elapsed'], 3),
        total_elapsed=round(timers['all']['elapsed'], 3),
    )

    if debug:
        csv_data.update(dict(
            debug_not_sliding_count=result['not_sliding_count'],
            debug_sliding_count=result['sliding_count'],
        ))
        for idx, voter in enumerate(
            zip(
                result['voter_decisions'],
                result['voter_not_sliding_counts'],
                result['voter_sliding_counts']
            )
        ):
            decision, ns_count, s_count = voter
            csv_data.update({
                f'debug_voter{idx}_decision': decision,
                f'debug_voter{idx}_not_sliding_count': ns_count,
                f'debug_voter{idx}_sliding_count': s_count,
            })
        for name, timings in timers.items():
            csv_data.update({
                f'debug_timer_elapsed_{name.replace(" ", "_")}': round(timings['elapsed'], 3),
            })

    with open(result_filename, 'w', newline='') as fp:
        fieldnames = list(csv_data.keys())
        writer = csv.DictWriter(
            fp,
            fieldnames=fieldnames,
            delimiter=',',
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerow(csv_data)

    print(f'PTX detected? {ptx_detected}')
    if debug:
        dbg(f'not sliding count: {result["not_sliding_count"]}, sliding count: {result["sliding_count"]}')
    print(f'Wrote detailed output to {result_filename}')

def cli_send_video(video_file, sock, debug=False):
    if not path.exists(video_file):
        print(f'File {video_file} does not exist')
        return None

    # create start_frame msg
    start_info = dict(video_file=path.abspath(video_file), debug=debug)

    if debug:
        dbg('Sending start message...')

    start_msg = Message(Message.Type.START, json.dumps(start_info).encode('ascii'))
    sock.send(start_msg)

    if debug:
        dbg('...start message sent.')
        dbg('Waiting on result message...')

    result = sock.recv()

    if debug:
        dbg('...result message received.')

    if result.type == Message.Type.RESULT:
        return json.loads(result.data)
    elif result.type == Message.Type.ERROR:
        print(f'Error encountered! {json.loads(result.data)}')
        return None
    else:
        raise Exception('Received message type that is not result nor error')


def main(args):
    handle = None
    try:
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        res = win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_MESSAGE, None, None)
        if res == 0:
            print(f'SetNamedPipeHandleState return code: {res}')
            return
        
        sock = WinPipeSock(handle)
        result = cli_send_video(args.video_file, sock, debug=args.debug)
        if result:
            write_result(args.video_file, result, debug=args.debug)
            return EXIT_SUCCESS
        return EXIT_FAILURE
    except pywintypes.error as e:
        code, source, message = e.args
        if code == winerror.ERROR_FILE_NOT_FOUND:
            print('Trying to connect to service...')
            start_service()
            raise Retry()
        elif code == winerror.ERROR_BROKEN_PIPE:
            print('Server hit an error condition')
            if path.exists(LOG_FILE):
                print(f'Last few lines of server log file ({LOG_FILE}):')
                # not memory efficient, but whatever for now
                with open(LOG_FILE, 'r') as fp:
                    lines = fp.read().strip().split('\n')
                for line in lines[-10:]:
                    print(f'\t{line}')
        elif code == winerror.ERROR_PIPE_BUSY:
            raise Retry()
        else:
            print('Unknown windows error:', e.args)
        return EXIT_FAILURE
    except Retry:
        raise
    except Exception as e:
        print('cli error:')
        traceback.print_exc()
        return EXIT_FAILURE
    finally:
        if handle:
            win32file.CloseHandle(handle)

if __name__ == '__main__':
    parser = prepare_argparser()
    args = parser.parse_args()
    retries = 0
    while retries < 3:
        try:
            sys.exit(main(args))
        except Retry:
            retries += 1
            time.sleep(1)
        except Exception as e:
            print('Fatal error:', e)
            sys.exit(EXIT_FAILURE)

    if path.exists(LOCK_FILE):
        print('The service is in preload phase. Please wait a minute for preload to finalize.')
    else:
        print('The service is not running or exited abnormally.')
        print(f'Please check {LOG_FILE} for details.')
    sys.exit(EXIT_FAILURE)
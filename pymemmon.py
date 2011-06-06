import sys
import psutil
import signal
import argparse
import logging

def run():
    parser = argparse.ArgumentParser(description='Kill runaway processes')
    parser.add_argument('-w', '--whitelist', help='Comma separated list of processes to monitor')
    parser.add_argument('-b', '--blacklist', help='Comma separated list of processes to ignore')
    parser.add_argument('-m', '--max-memory', help='Max memory for a process in megabytes, default is 100mb')
    parser.add_argument('-s', '--signal', help='The signal to send to the process, default is SIGUSR1')
    parser.add_argument('-l', '--log-level', help='The amount of logging you want: INFO, DEBUG, or ERROR')
    parser.add_argument('-f', '--log-file', help='File to log to')

    args = parser.parse_args(sys.argv[1:])
    check_processes(args.max_memory, args.whitelist, args.blacklist, args.signal, args.log_level, args.log_file)

def check_processes(max_memory, whitelist, blacklist, sig, log_level, log_file):
    # set sane defaults
    if  max_memory:
        # convert arg to bytes
        max_memory = max_memory * (1024 * 1024)
    else:
        # default max memory to 100mb
        MAX_MEM = 100 * (1024 * 1024)
        max_memory = MAX_MEM

    if sig:
        sig = getattr(signal, sig.strip().upper(), signal.SIGUSR1)
    else:
        sig = signal.SIGUSR1

    if log_level:
        log_level = getattr(logging, log_level.strip().upper(), logging.ERROR)
    else:
        log_level = logging.ERROR

    LOG_FORMAT='%(asctime)s %(message)s'

    if log_file:
        logging.basicConfig(format=LOG_FORMAT, level=log_level, filename=log_file)
    else:
        logging.basicConfig(format=LOG_FORMAT, level=log_level)

    if whitelist:
        whitelist = whitelist.strip().split(',')

    if blacklist:
        blacklist = blacklist.strip().split(',')

    procs = psutil.get_process_list()

    for proc in procs:
        try:
            # if a whitelist is defined, make sure the process is in it
            if whitelist:
                if not proc.name in whitelist:
                    continue

            # if a blacklist is defined, make sure the process is not in it
            if blacklist:
                if proc.name in blacklist:
                    continue

            mem = proc.get_memory_info()[0]
            if mem >= max_memory:
                logging.info('Killing %s at memory %s mb' % (proc.name, mem / (1024 * 1024)))
                name = proc.name
                # keep sending the signal until the process dies
                IS_ALIVE = True
                while IS_ALIVE:
                    try:
                        proc.send_signal(sig)
                    except psutil.error.NoSuchProcess:
                        logging.info('Process %s has been killed' % name)
                        IS_ALIVE = False

#                send_mail(proc.name, mem)
        except psutil.error.AccessDenied as exc:
            logging.error('Do not have access to %s' % exc.msg)
            pass

#def send_mail(proc, mem):
#    import smtplib
#    from email.MIMEText import MIMEText
#    msg = MIMEText('Had to kill %(process)s it was using %(memory)s megs of memory' % {
#        'process': proc,
#        'memory': (mem / 1024) / 1024,
#    })
#    
#    sender = 'sontek@gmail.com'
#    recipient = 'sontek@gmail.com'
#
#    msg['Subject'] = 'Killed a process' 
#    msg['From'] = sender
#    msg['To'] = recipient
#
#    s = smtplib.SMTP()
#    s.connect()
#    s.sendmail(sender, [recipient], msg.as_string())
#    s.close()
#

if __name__ == '__main__':
    run()


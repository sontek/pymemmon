import sys
import psutil
import signal
import argparse
import logging

class Memmon(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Kill runaway processes')
        parser.add_argument('-w', '--whitelist', help='Comma separated list of processes to monitor, will only monitor these if defined')
        parser.add_argument('-b', '--blacklist', help='Comma separated list of processes to ignore')
        parser.add_argument('-m', '--max-memory', help='Max memory for a process in megabytes, default is 100mb')
        parser.add_argument('-s', '--signal', help='The signal to send to the process, default is SIGUSR1')
        parser.add_argument('-l', '--log-level', help='The amount of logging you want: INFO, DEBUG, or ERROR')
        parser.add_argument('-f', '--log-file', help='File to log to')
        parser.add_argument('-e', '--send-mail', action='store_true', help='Will attempt to notify via e-mail if this is set')
        parser.add_argument('--smtp-host', help='The smtp server address you want to send notifications through')
        parser.add_argument('--smtp-port', help='The port the smtp server listens on')
        parser.add_argument('--smtp-user', help='The username to authenticate as')
        parser.add_argument('--smtp-password', help='The password to use for the smtp server')
        parser.add_argument('--smtp-from', help='Who the e-mail is coming from')
        parser.add_argument('--smtp-recipients', help='The people to be notified, comma separated list')

        args = parser.parse_args(sys.argv[1:])

        # set sane defaults
        self.whitelist = None
        self.blacklist = ['mds']

        self.should_send_mail = False
        if args.send_mail:
            self.should_send_mail = True

            if not args.smtp_recipients:
                raise Exception('You must define who you want the notifications to go to with --smtp-recipients')
            else:
                self.smtp_recipients = args.smtp_recipients.strip().split(',')

            if not args.smtp_from:
                raise Exception('You must define who the notifications should come from with --smtp-from')
            else:
                self.smtp_from = args.smtp_from.strip()

        if  args.max_memory:
            # convert arg to bytes
            self.max_memory = args.max_memory * (1024 * 1024)
        else:
            # default max memory to 100mb
            MAX_MEM = 100 * (1024 * 1024)
            self.max_memory = MAX_MEM

        if args.signal:
            self.sig = getattr(signal, args.signal.strip().upper(), signal.SIGUSR1)
        else:
            self.sig = signal.SIGUSR1

        if args.log_level:
            self.log_level = getattr(logging, args.log_level.strip().upper(), logging.ERROR)
        else:
            self.log_level = logging.ERROR

        self.LOG_FORMAT='%(asctime)s %(message)s'

        if args.log_file:
            logging.basicConfig(format=self.LOG_FORMAT, level=args.log_level, filename=args.log_file)
        else:
            logging.basicConfig(format=self.LOG_FORMAT, level=args.log_level)

        if args.whitelist:
            self.whitelist = args.whitelist.strip().split(',')

        if args.blacklist:
            self.blacklist += args.blacklist.strip().split(',')

        if args.smtp_host:
            self.smtp_host = args.smtp_host.strip()
        else:
            self.smtp_host = 'localhost'

        if args.smtp_port:
            try:
                self.smtp_port = int(args.smtp_port.strip())
            except:
                self.smtp_port = 25
        else:
            self.smtp_port = 25

        if args.smtp_user:
            self.smtp_user = args.smtp_user.strip()

        if args.smtp_password:
            self.smtp_password = args.smtp_password.strip()

    def check_processes(self):
        procs = psutil.get_process_list()

        for index, proc in enumerate(procs):
            try:
                # if a whitelist is defined, make sure the process is in it
                if self.whitelist:
                    if not proc.name in self.whitelist:
                        continue

                # if a blacklist is defined, make sure the process is not in it
                if self.blacklist:
                    if proc.name in self.blacklist:
                        continue

                mem = proc.get_memory_info()[0]

                if mem >= self.max_memory:
                    logging.info('Killing %s at memory %s mb' % (proc.name, mem / (1024 * 1024)))
                    name = proc.name
                    # keep sending the signal until the process dies
                    IS_ALIVE = True
                    while IS_ALIVE:
                        try:
                            proc.send_signal(self.sig)
                        except psutil.error.NoSuchProcess:
                            logging.info('Process %s has been killed' % name)
                            IS_ALIVE = False

                    if not IS_ALIVE:
                        if self.should_send_mail:
                            self.send_mail(name, mem)

            except psutil.error.AccessDenied as exc:
                logging.error('Do not have access to %s' % exc.msg)
                pass

    def send_mail(self, name, mem):
        import smtplib
        from email.MIMEText import MIMEText

        msg = MIMEText('Had to kill %(process)s it was using %(memory)s megs of memory' % {
            'process': name,
            'memory': mem / (1024 * 1024),
        })

        msg['Subject'] = 'Killed a process' 
        msg['From'] = self.smtp_from
        msg['To'] = ', '.join(self.smtp_recipients)

        mailServer = smtplib.SMTP(self.smtp_host, self.smtp_port)
        mailServer.ehlo()
        mailServer.starttls()
        mailServer.ehlo()

        if self.smtp_user and self.smtp_password:
            mailServer.login(self.smtp_user, self.smtp_password)

        mailServer.sendmail(self.smtp_user, self.smtp_recipients, msg.as_string())
        mailServer.close()

if __name__ == '__main__':
    monitor = Memmon()
    monitor.check_processes()



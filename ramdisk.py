from subprocess import call
import ConfigParser
import abc
import argparse


class Ramdisk(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def start_ramdisk(self, ramdisk_name, ramdisk_size_mb):
        """Create ramdisk on the operating system"""
        raise NotImplementedError

    @abc.abstractmethod
    def ramdisk_dir(self, ramdisk_name):
        """Return a path to system ramdisk"""
        raise NotImplementedError

    @abc.abstractmethod
    def shutdown_ramdisk(self, ramdisk_dir):
        """Shutdown ramdisk that was created on the operating system"""
        raise NotImplementedError

    @abc.abstractmethod
    def start_mysql(self, ramdisk_dir, mysql_dir, mysql_user, mysql_password, executable_sqls):
        """Start MySQL on the ramdisk and execute provided sqls"""
        raise NotImplementedError

    @abc.abstractmethod
    def shutdown_mysql(self, mysql_dir, mysql_user, mysql_password):
        """Shutdown MySQL that was started on ramdisk"""
        raise NotImplementedError


class MacRamdisk(Ramdisk):

    def start_ramdisk(self, ramdisk_name, ramdisk_size_mb):
        size = ramdisk_size_mb * 2048
        start_ramdisk_command = 'diskutil erasevolume HFS+ "%s" `hdiutil attach -nomount ram://%s`' % (ramdisk_name, size)
        call(start_ramdisk_command, shell=True)

    def ramdisk_dir(self, ramdisk_name):
        ramdisk_dir = '/Volumes/%s' % (ramdisk_name)
        return ramdisk_dir

    def shutdown_mysql(self, mysql_dir, mysql_user, mysql_password):
        shutdown_mysql_command = '%s/bin/mysqladmin -u%s -p%s shutdown' % (mysql_dir, mysql_user, mysql_password)
        call(shutdown_mysql_command, shell=True)

    def shutdown_ramdisk(self, ramdisk_dir):
        shutdown_ramdisk_command = 'diskutil unmount %s' % (ramdisk_dir)
        call(shutdown_ramdisk_command, shell=True)

    def _reset_mysql_password(self, mysql_user, mysql_password):
        mysql_command = 'mysql -e "UPDATE mysql.user SET \
                                authentication_string=password(\'%s\'), \
                                password_expired=\'N\', \
                                password_last_changed=now(), \
                                account_locked=\'N\', \
                                password_lifetime=null \
                                WHERE user=\'%s\'"' % (mysql_password, mysql_user)
        call(mysql_command, shell=True)

    def start_mysql(self, ramdisk_dir, mysql_dir, mysql_user, mysql_password, executable_sqls):
        copy_mysql_command = '%s/bin/mysqld --initialize --basedir=%s --datadir=%s' % (mysql_dir, mysql_dir, ramdisk_dir)
        call(copy_mysql_command, shell=True)

        start_command = '%s/bin/mysql.server start --skip-grant-tables' % (mysql_dir)
        call(start_command, shell=True)

        self._reset_mysql_password(mysql_user, mysql_password)

        for sql in executable_sqls:
            mysql_command = 'mysql -e "%s"' % (sql.replace('`', '\`'))
            call(mysql_command, shell=True)
        call('mysql -e "FLUSH PRIVILEGES"', shell=True)


if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description='')
    arg_parser.add_argument('--stop', action='store_true', help='shutdown ramdisk and MySQL')
    args = arg_parser.parse_args()

    config = ConfigParser.ConfigParser(allow_no_value=True)
    config.read('config.ini')

    mysql_user = 'root'
    mysql_config = dict(config.items('mysql'))
    mysql_dir = mysql_config.get('directory')
    mysql_password = mysql_config.get('password')

    ramdisk_config = dict(config.items('ramdisk'))
    ramdisk_name = ramdisk_config.get('name')
    ramdisk_size_mb = int(ramdisk_config.get('size_mb'))

    parsed_sqls = config.options('executablesql')
    executable_sqls = set()

    for sql in parsed_sqls:
        if len(sql) > 0:
            executable_sqls.add(sql)

    ramdisk = MacRamdisk()
    ramdisk_dir = ramdisk.ramdisk_dir(ramdisk_name)
    if not args.stop:
        ramdisk.start_ramdisk(ramdisk_name, ramdisk_size_mb)
        ramdisk.start_mysql(ramdisk_dir, mysql_dir, mysql_user, mysql_password, executable_sqls)
    else:
        ramdisk.shutdown_mysql(mysql_dir, mysql_user, mysql_password)
        ramdisk.shutdown_ramdisk(ramdisk_dir)

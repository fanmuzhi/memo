#!/usr/bin/env python
# encoding: utf-8
###############################################################################
#
#  This fabric.py is used to setup programs on a new CentOS6.4 mini server.
#  And the detail task is to setup the network, apache, php, mysql, etc,.
#  -- qibo
#  -- 2013-05-30
#
###############################################################################

from fabric.api import run, put, env, cd

env.hosts = ['172.23.6.223']
#env.hosts = ['192.168.0.106']
env.user = "root"
env.password = "qibo@cypress"

env.db_user = "qibo"
env.db_password = "qibo@cypress"
env.db_name = "trackpad"


def message():
    # for testing the connection
    run("uname -a")


def set_yumproxy():
    run("echo proxy=http://rootproxy.cypress.com:8080 >> /etc/yum.conf")


def install_svn():
    run("yum -y install svn")
    run("svn --version")


def install_apache():
    run("yum -y install httpd")

    # change httpd.conf
    run("sed -i 's/ServerAdmin root@localhost/ServerAdmin qibo@cypress.com/g' "
        "/etc/httpd/conf/httpd.conf")

    run("sed -i 's/#ServerName www.example.com:80/ServerName %s:80/g' "
        "/etc/httpd/conf/httpd.conf" % env.hosts[0])

    # Open port 80 and start service
    # insert port 80 to iptables chain INPUT line 5
    # don't use -A to append to the chain
    run("iptables -I INPUT 5 -m state --state "
        "NEW -m tcp -p tcp --dport 80 -j ACCEPT")
    run("iptables -I INPUT 5 -m state --state "
        "NEW -m tcp -p tcp --dport 443 -j ACCEPT")
    run("service iptables save")
    run("service iptables restart")

    # add httpd to start service and start httpd
    run("chkconfig --level 2345 httpd on; service httpd start")


def install_mysql():
    run("yum -y install mysql mysql-server")

    # checkout and cp my.cnf
    run("cp ~/config_files/my.cnf /etc/my.cnf")

    # open port 3306
    run("iptables -I INPUT 5 -m state --state "
        "NEW -m tcp -p tcp --dport 3306 -j ACCEPT")
    run("iptables -I INPUT 5 -m state --state "
        "NEW -m udp -p udp --dport 3306 -j ACCEPT")
    run("service iptables save")
    run("service iptables restart")

    # start service
    run("chkconfig --level 2345 mysqld on; service mysqld start")

    # delete mysql users except root@local
    command = ('delete from mysql.user where '
               'not (host="localhost" and user="root");')
    run("mysql -u root -e '%s' " %
        (command))

    # change root password
    command = ('SET PASSWORD FOR "root"@"localhost" = PASSWORD("%s");' %
               (env.db_password))
    run("mysql -u root -e '%s' " %
        (command))
    run("mysql -u root -p'%s' -e 'FLUSH PRIVILEGES;'" %
        (env.db_password))


def install_rsync():
    run("yum -y install rsync")
    run("rsync --version")


def install_php():
    run("yum -y install php php-pecl-apc php-mysql php-pdo")


def put_files():
    #run("mkdir ~/config_files", warn_only=True)
    put("./config_files", "~/")


def setup_database():
    # create tables from the sql script
    command = 'source ~/config_files/database_structure.sql'
    run("mysql -u root -p'%s' -e '%s' " %
        (env.db_password, command))

    # create user for particular table
    command = ('GRANT ALL PRIVILEGES ON {0}.* TO "{0}"@"%" '
               'IDENTIFIED BY "{0}";'.format(env.db_name))
    run("mysql -u root -p'%s' -e '%s' " %
        (env.db_password, command))
    run("mysql -u root -p'%s' -e 'FLUSH PRIVILEGES;'" %
        (env.db_password))


def svn_co_files():
    # checkout the website program from svn server
    run("svn co http://172.23.6.12/repos/BMOChina/Public/Source/"
        "Macross/trunk /var/www/html/")

    # restore the file contexts
    run("restorecon -rv /var/www/html")

    # restart the service
    run("service httpd restart")


def install_memcached():
    run("yum install memcached")
    run("chkconfig --level 2345 memcached on")
    run("service memcached start")
    run("yum install php-pecl-memcache")


def set_selinux():
    # allow httpd to connect datbase and memcache
    run("setsebool -P httpd_can_network_connect 1")
    run("setsebool -P httpd_can_network_connect_db 1")
    run("setsebool -P httpd_can_network_memcache 1")
    run("setsebool -P httpd_can_network_relay 1")


def deploy():
    '''the main function to deploy the system installation.
    use the command in the shell: fab deploy
    '''
    message()
    set_yumproxy()
    set_selinux()
    put_files()

    install_svn()
    install_rsync()
    install_apache()
    install_mysql()
    install_php()

    setup_database()
    svn_co_files()


def update():
    '''the update funtion to auto update the website program.
    use the command in the shell: fab update
    '''
    with cd("/var/www/html"):
        run("svn update")
        run("restorecon -rv /var/www/html")
        run("service httpd restart")

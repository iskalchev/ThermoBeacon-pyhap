#!/bin/sh
#
# a simple way to parse shell script arguments
# 
# please edit and use to your hearts content
# 
COMMAND=""
MAC=""

usage()
{
echo "if this was a real script you would see something useful here"
echo ""
echo "./simple_args_parsing.sh"
echo "\t-h --help"
echo "\t--environment=$ENVIRONMENT"
echo "\t--db-path=$DB_PATH"
echo ""
}
while [ "$1" != "" ]; do
    PARAM=`echo $1 | awk -F= '{print $1}'`
    VALUE=`echo $1 | awk -F= '{print $2}'`
case $PARAM in
        -h | --help)
            usage
exit
            ;;
        --mac)
            MAC=$VALUE
            ;;
        list | add | listen | identify | remove )
            COMMAND=$PARAM
            ;;
*)
echo "ERROR: unknown parameter \"$PARAM\""
            usage
exit 1
            ;;
esac
shift
done

echo $COMMAND | socat -t 2 - udp:127.0.0.1:9999


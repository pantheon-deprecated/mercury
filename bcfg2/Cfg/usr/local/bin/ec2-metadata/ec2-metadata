#!/bin/bash
#
#########################################################################
#This software code is made available "AS IS" without warranties of any #
#kind. You may copy, display, modify and redistribute the software      #
#code either by itself or as incorporated into your code; provided that #
#you do not remove any proprietary notices. Your use of this software   #
#code is at your own risk and you waive any claim against Amazon        #
#Digital Services, Inc. or its affiliates with respect to your use of   #
#this software code. (c) 2006-2007 Amazon Digital Services, Inc. or its #
#affiliates.                                                            #
#########################################################################

function print_help()
{
echo "ec2-metadata v0.1
Use to retrieve EC2 instance metadata from within a running EC2 instance. 
e.g. to retrieve instance id: ec2-metadata -i
     to retrieve ami id: ec2-metadata -a
     to get help: ec2-metadata --help
For more information on Amazon EC2 instance meta-data, refer to the documentation at
http://docs.amazonwebservices.com/AWSEC2/2008-05-05/DeveloperGuide/AESDG-chapter-instancedata.html

Usage: ec2-metadata <option>
Options:
--all                     Show all metadata information for this host (also default).
-a/--ami-id               The AMI ID used to launch this instance
-l/--ami-launch-index     The index of this instance in the reservation (per AMI).
-m/--ami-manifest-path    The manifest path of the AMI with which the instance was launched.
-n/--ancestor-ami-ids     The AMI IDs of any instances that were rebundled to create this AMI.
-b/--block-device-mapping Defines native device names to use when exposing virtual devices.
-i/--instance-id          The ID of this instance
-t/--instance-type        The type of instance to launch. For more information, see Instance Types.
-h/--local-hostname       The local hostname of the instance.
-o/--local-ipv4           Public IP address if launched with direct addressing; private IP address if launched with public addressing.
-k/--kernel-id            The ID of the kernel launched with this instance, if applicable.
-z/--availability-zone    The availability zone in which the instance launched. Same as placement
-c/--product-codes        Product codes associated with this instance.
-p/--public-hostname      The public hostname of the instance.
-v/--public-ipv4          NATted public IP Address
-u/--public-keys          Public keys. Only available if supplied at instance launch time
-r/--ramdisk-id           The ID of the RAM disk launched with this instance, if applicable.
-e/--reservation-id       ID of the reservation.
-s/--security-groups      Names of the security groups the instance is launched in. Only available if supplied at instance launch time
-d/--user-data            User-supplied data.Only available if supplied at instance launch time."
}

#check some basic configurations before running the code
function chk_config()
{
 #check if run inside an ec2-instance
 x=$(curl -s http://169.254.169.254/)
 if [ $? -gt 0 ]; then
    echo '[ERROR] Command not valid outside EC2 instance. Please run this command within a running EC2 instance.'
    exit 1
 fi
}

#print ami-id
function print_ami-id()
{
echo -n 'ami-id: '
x=$(curl -s http://169.254.169.254/latest/meta-data/ami-id)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print ami-launch-index
function print_ami-launch-index()
{
echo -n 'ami-launch-index: '
x=$(curl -s http://169.254.169.254/latest/meta-data/ami-launch-index)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print ami-manifest-path
function print_ami-manifest-path()
{
echo -n 'ami-manifest-path: '
x=$(curl -s http://169.254.169.254/latest/meta-data/ami-manifest-path)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print ancestor-amis
function print_ancestor-ami-ids()
{
echo -n 'ancestor-ami-ids: '
x=$(curl -s http://169.254.169.254/latest/meta-data/ancestor-ami-ids)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print block-device-mapping
function print_block-device-mapping()
{
echo 'block-device-mapping: '
x=$(curl -s http://169.254.169.254/latest/meta-data/block-device-mapping/)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   for i in $x; do
       echo -e '\t' $i: $(curl -s http://169.254.169.254/latest/meta-data/block-device-mapping/$i)
   done
   else
   echo not available
fi
}

#print instance-id
function print_instance-id()
{
echo -n 'instance-id: '
x=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print instance-type
function print_instance-type()
{
echo -n 'instance-type: '
x=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then 
   echo $x
   else
   echo not available
fi
}

#print local-hostname
function print_local-hostname()
{
echo -n 'local-hostname: '
x=$(curl -s http://169.254.169.254/latest/meta-data/local-hostname)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print local-ipv4
function print_local-ipv4()
{
echo -n 'local-ipv4: '
x=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print kernel-id
function print_kernel-id()
{
echo -n 'kernel-id: '
x=$(curl -s http://169.254.169.254/latest/meta-data/kernel-id)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print placement
function print_placement()
{
echo -n 'placement: '
x=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print product-codes
function print_product-codes()
{
echo -n 'product-codes: '
x=$(curl -s http://169.254.169.254/latest/meta-data/product-codes)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print public-hostname
function print_public-hostname()
{
echo -n 'public-hostname: '
x=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print public-ipv4
function print_public-ipv4()
{
echo -n 'public-ipv4: '
x=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print public-keys
function print_public-keys()
{
echo 'public-keys: '
x=$(curl -s http://169.254.169.254/latest/meta-data/public-keys/)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   for i in $x; do
   index=$(echo $i|cut -d = -f 1)
   keyname=$(echo $i|cut -d = -f 2)
   echo keyname:$keyname
   echo index:$index
   format=$(curl -s http://169.254.169.254/latest/meta-data/public-keys/$index/)
   echo format:$format
   echo 'key:(begins from next line)'
   echo $(curl -s http://169.254.169.254/latest/meta-data/public-keys/$index/$format)
   done
   else
   echo not available
fi
}

#print ramdisk-id
function print_ramdisk-id()
{
echo -n 'ramdisk-id: '
x=$(curl -s http://169.254.169.254/latest/meta-data/ramdisk-id)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print reservation-id
function print_reservation-id()
{
echo -n 'reservation-id: '
x=$(curl -s http://169.254.169.254/latest/meta-data/reservation-id)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print security-groups
function print_security-groups()
{
echo -n 'security-groups: '
x=$(curl -s http://169.254.169.254/latest/meta-data/security-groups)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

#print user data
function print_user_data()
{
echo -n 'user-data: '
x=$(curl -s http://169.254.169.254/latest/user-data)
if [ $(echo $x|grep 404|wc -l) -eq 0 ]; then
   echo $x
   else
   echo not available
fi
}

function print_all()
{
print_ami-id
print_ami-launch-index
print_ami-manifest-path
print_ancestor-ami-ids
print_block-device-mapping
print_instance-id
print_instance-type
print_local-hostname
print_local-ipv4
print_kernel-id
print_placement
print_product-codes
print_public-hostname
print_public-ipv4
print_public-keys
print_ramdisk-id
print_reservation-id
print_security-groups
print_user_data
}

#check if run inside an EC2 instance
chk_config

#command called in default mode
if [ "$#" -eq 0 ]; then
print_all
fi

#start processing command line arguments
while [ "$1" != "" ]; do
    case $1 in
        -a | --ami-id )                print_ami-id
                                       ;;
        -l | --ami-launch-index )      print_ami-launch-index
                                       ;;
	-m | --ami-manifest-path )     print_ami-manifest-path
	                               ;;
	-n | --ancestor-ami-ids )      print_ancestor-ami-ids
	                               ;;
        -b | --block-device-mapping )  print_block-device-mapping
                                       ;;
	-i | --instance-id )           print_instance-id
	                               ;;
        -t | --instance-type )         print_instance-type
                                       ;;
	-h | --local-hostname )        print_local-hostname
	                               ;;
	-o | --local-ipv4 )            print_local-ipv4
	                               ;;
	-k | --kernel-id )             print_kernel-id
	                               ;;
	-z | --availability-zone )     print_placement
	                               ;;
	-c | --product-codes )         print_product-codes
	                               ;;
	-p | --public-hostname )       print_public-hostname
	                               ;;
	-v | --public-ipv4 )           print_public-ipv4
	                               ;;
	-u | --public-keys )           print_public-keys
	                               ;;
	-r | --ramdisk-id )            print_ramdisk-id
	                               ;;
	-e | --reservation-id )        print_reservation-id
	                               ;;
	-s | --security-groups )       print_security-groups
	                               ;;
	-d | --user-data )             print_user_data
                                       ;;
        -h | --help )                  print_help
                                       exit
                                       ;;
        --all )                        print_all
	                               exit 
	                               ;;
        * )                            print_help
                                       exit 1
    esac
    shift
done

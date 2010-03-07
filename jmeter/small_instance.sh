#!/bin/bash

#script to fire off automated jmeter tests and print pretty graphs.
#the test file should have the following variables:
#DRUPAL_HOST
#DRUPAL_USER
#DRUPAL_PASS
#JMETER_THREADS
#JMETER_LOOPS
#DRUPAL_BASE_PATH
#JMETER_LOG_DIR

#config:

TEST_NAME="mercury_1.0_64" #no spaces please
TEST_FILE="tests/default.jmx"
DRUPAL_HOST=""
DRUPAL_BASE_PATH="" #ie, use "pressflow" if drupal site is http://drupal_site/pressflow/
DRUPAL_USER="admin" #valid username on drupal host
DRUPAL_PASS="drupal" #ditto

JMETER_THREADS=5 #default 5
JMETER_LOOPS=10  #default 10
NUM_THREADS=5 #add this number of threads each test - default 5
NUM_LOOPS=5 #add this number of loops each test - default 5
NUM_TESTS=3 #default 3
TEST_COUNT=0

#program

BASE_DIR=`pwd`

while [ $TEST_COUNT -lt $NUM_TESTS ]; do 
    JMETER_LOG_DIR="$BASE_DIR/results/$DRUPAL_HOST/$TEST_NAME/$TEST_COUNT"

    mkdir -p $JMETER_LOG_DIR
    touch $JMETER_LOG_DIR/${JMETER_THREADS}threads${JMETER_LOOPS}loops
    cp $BASE_DIR/$TEST_FILE $JMETER_LOG_DIR.jmx
    
#create jmeter test:
    sed -i s/DRUPAL_HOST/$DRUPAL_HOST/ $JMETER_LOG_DIR.jmx
    sed -i s/DRUPAL_USER/${DRUPAL_USER}/ $JMETER_LOG_DIR.jmx
    sed -i s/DRUPAL_PASS/${DRUPAL_PASS}/ $JMETER_LOG_DIR.jmx
    sed -i s/JMETER_THREADS/${JMETER_THREADS}/ $JMETER_LOG_DIR.jmx
    sed -i s/JMETER_LOOPS/${JMETER_LOOPS}/ $JMETER_LOG_DIR.jmx
    sed -i s*DRUPAL_BASE_PATH*${DRUPAL_BASE_PATH}* $JMETER_LOG_DIR.jmx
    sed -i s*JMETER_LOG_DIR*${JMETER_LOG_DIR}* $JMETER_LOG_DIR.jmx
    
#run test:
    $BASE_DIR/bin/jmeter -n -t $JMETER_LOG_DIR.jmx -l $JMETER_LOG_DIR.xml
    $BASE_DIR/bin/jmetergraph.pl $JMETER_LOG_DIR.xml
    mv $BASE_DIR/*.png $JMETER_LOG_DIR/

    JMETER_THREADS=$(($JMETER_THREADS+$NUM_THREADS))
    JMETER_LOOPS=$(($JMETER_LOOPS+$NUM_LOOPS))
    TEST_COUNT=$(($TEST_COUNT+1))
done 

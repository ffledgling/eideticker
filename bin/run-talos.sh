#!/bin/bash

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Eideticker.
#
# The Initial Developer of the Original Code is
# Mozilla foundation
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   William Lachance <wlachance@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

set -e

kill_bcontrollers () {
    BCONTROLLER_PIDS=`ps ax | grep bcontroller.py | grep -v grep | cut -d ' ' -f 1`
    for PID in $BCONTROLLER_PIDS; do
        echo "Killing zombie bcontroller process: $PID"
        kill -9 $PID
    done
}

TEST=$1
BINDIR=$(dirname $0)
TALOS_DIR=$(dirname $0)/../src/talos

if [ ! $TEST ]; then
    echo "Must specify a valid test name!"
    exit 1
fi

source $BINDIR/activate

# Kill any current bcontroller processes and set up a trap on exit to do the
# same. Stop zombies!
kill_bcontrollers
trap kill_bcontrollers INT TERM EXIT

cd $TALOS_DIR && python run_tests.py -d -n eideticker-$TEST.config

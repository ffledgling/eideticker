#!/usr/bin/env python

import datetime
import eideticker
import json
import os
import re
import sys
import tempfile
import time
import videocapture

CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "../captures")
PROFILE_DIR = os.path.join(os.path.dirname(__file__), "../profiles")
CHECKERBOARD_REGEX = re.compile('.*GeckoLayerRendererProf.*1000ms:.*\ '
                                '([0-9]+\.[0-9]+)\/([0-9]+).*')

def parse_checkerboard_log(fname):
    checkerboarding_percent_totals = 0.0
    with open(fname) as f:
        for line in f.readlines():
            match = CHECKERBOARD_REGEX.search(line.rstrip())
            if match:
                (amount, total) = (float(match.group(1)), float(match.group(2)))
                checkerboarding_percent_totals += (total - amount)

    return checkerboarding_percent_totals

def runtest(device_prefs, testname, options, apk=None, appname = None,
            appdate = None):
    device = None
    if apk:
        appinfo = eideticker.get_fennec_appinfo(apk)
        appname = appinfo['appname']
        print "Installing %s (version: %s, revision %s)" % (appinfo['appname'],
                                                            appinfo['version'],
                                                            appinfo['revision'])
        device = eideticker.getDevice(**device_prefs)
        device.updateApp(apk)
    else:
        appinfo = None

    captures = []

    for i in range(options.num_runs):
        # Kill any existing instances of the processes (for Android)
        if device:
            device.killProcess(appname)

        # Now run the test
        curtime = int(time.time())
        capture_file = os.path.join(CAPTURE_DIR,
                                    "metric-test-%s-%s.zip" % (appname,
                                                               curtime))
        if options.enable_profiling:
            profile_file = os.path.join(PROFILE_DIR,
                                        "profile-%s-%s.zip" % (appname, curtime))
        else:
            profile_file = None

        if options.get_internal_checkerboard_stats:
            checkerboard_log_file = tempfile.NamedTemporaryFile()
        else:
            checkerboard_log_file = None

        current_date = time.strftime("%Y-%m-%d")
        capture_name = "%s - %s (taken on %s)" % (testname, appname, current_date)

        eideticker.run_test(testname, options.capture_device,
                            appname, capture_name, device_prefs,
                            extra_prefs=options.extra_prefs,
                            extra_env_vars=options.extra_env_vars,
                            checkerboard_log_file=checkerboard_log_file,
                            profile_file=profile_file,
                            no_capture=options.no_capture,
                            capture_file=options.capture_file,
                            sync_time=options.sync_time)

        capture_result = {}
        if not options.no_capture:
            capture_result['file'] = capture_file

            capture = videocapture.Capture(capture_file)

            if options.startup_test:
                capture_result['stableframe'] = videocapture.get_stable_frame(capture)
            else:
                capture_result['uniqueframes'] = videocapture.get_num_unique_frames(capture)
                capture_result['fps'] = videocapture.get_fps(capture)
                capture_result['checkerboard'] = videocapture.get_checkerboarding_area_duration(capture)
            if options.outputdir:
                video_path = os.path.join('videos', 'video-%s.webm' % time.time())
                video_file = os.path.join(options.outputdir, video_path)
                open(video_file, 'w').write(capture.get_video().read())
                capture_result['video'] = video_path

        if options.enable_profiling:
            capture_result['profile'] = profile_file

        if options.get_internal_checkerboard_stats:
            internal_checkerboard_totals = parse_checkerboard_log(checkerboard_log_file.name)
            capture_result['internalcheckerboard'] = internal_checkerboard_totals

        captures.append(capture_result)

    appkey = appname
    if appdate:
        appkey = appdate.isoformat()
    else:
        appkey = appname

    if appinfo and appinfo.get('revision'):
        display_key = "%s (%s)" % (appkey, appinfo['revision'])
    else:
        display_key = appkey
    print "=== Results for %s ===" % display_key

    if not options.no_capture:
        if options.startup_test:
            print "  First stable frames:"
            print "  %s" % map(lambda c: c['stableframe'], captures)
            print
        else:
            print "  Number of unique frames:"
            print "  %s" % map(lambda c: c['uniqueframes'], captures)
            print

            print "  Average number of unique frames per second:"
            print "  %s" % map(lambda c: c['fps'], captures)
            print

            print "  Checkerboard area/duration (sum of percents NOT percentage):"
            print "  %s" % map(lambda c: c['checkerboard'], captures)
            print

        print "  Capture files:"
        print "  Capture files: %s" % map(lambda c: c['file'], captures)
        print

    if options.enable_profiling:
        print "  Profile files:"
        print "  Profile files: %s" % map(lambda c: c['profile'], captures)
        print

    if options.get_internal_checkerboard_stats:
        print "  Internal Checkerboard Stats (sum of percents, not percentage):"
        print "  %s" % map(lambda c: c['internalcheckerboard'], captures)
        print

    if options.outputdir:
        outputfile = os.path.join(options.outputdir, "metric-test-%s.json" % time.time())
        resultdict = { 'title': testname, 'data': {} }
        if os.path.isfile(outputfile):
            resultdict.update(json.loads(open(outputfile).read()))

        if not resultdict['data'].get(appkey):
            resultdict['data'][appkey] = []
        resultdict['data'][appkey].extend(captures)

        with open(outputfile, 'w') as f:
            f.write(json.dumps(resultdict))

def main(args=sys.argv[1:]):
    usage = "usage: %prog <test> [appname1] [appname2] ..."
    parser = eideticker.TestOptionParser(usage=usage)
    parser.add_option("--num-runs", action="store",
                      type = "int", dest = "num_runs",
                      default=1,
                      help = "number of runs (default: 1)")
    parser.add_option("--output-dir", action="store",
                      type="string", dest="outputdir",
                      help="output results to json file")
    parser.add_option("--no-capture", action="store_true",
                      dest = "no_capture",
                      help = "run through the test, but don't actually "
                      "capture anything")
    parser.add_option("--enable-profiling", action="store_true",
                      dest = "enable_profiling",
                      help="Collect performance profiles using the built in profiler.")
    parser.add_option("--get-internal-checkerboard-stats",
                      action="store_true",
                      dest="get_internal_checkerboard_stats",
                      help="get and calculate internal checkerboard stats")
    parser.add_option("--startup-test",
                      action="store_true",
                      dest="startup_test",
                      help="measure startup times instead of normal metrics")
    parser.add_option("--url-params", action="store",
                      dest="url_params", default="",
                      help="additional url parameters for test")
    parser.add_option("--use-apks", action="store_true", dest="use_apks",
                      help="use and install android APKs as part of test (instead of specifying appnames)")
    parser.add_option("--date", action="store", dest="date",
                      metavar="YYYY-MM-DD",
                      help="get and test nightly build for date")
    parser.add_option("--start-date", action="store", dest="start_date",
                      metavar="YYYY-MM-DD",
                      help="start date for range of nightlies to test")
    parser.add_option("--end-date", action="store", dest="end_date",
                      metavar="YYYY-MM-DD",
                      help="end date for range of nightlies to test")

    options, args = parser.parse_args()

    if len(args) == 0:
        parser.error("Must specify at least one argument: the path to the test")

    dates = []
    appnames = []
    apks = []
    if options.start_date and options.end_date and len(args) == 1:
        testname = args[0]
        start_date = eideticker.BuildRetriever.get_date(options.start_date)
        end_date = eideticker.BuildRetriever.get_date(options.end_date)
        days=(end_date-start_date).days
        for numdays in range(days+1):
            dates.append(start_date+datetime.timedelta(days=numdays))
    elif options.date and len(args) == 1:
        testname = args[0]
        dates = [eideticker.BuildRetriever.get_date(options.date)]
    elif not options.date and len(args) >= 2:
        testname = args[0]
        if options.use_apks:
            apks = args[1:]
        else:
            appnames = args[1:]
    elif not options.date or (not options.start_date and not options.end_date):
        parser.error("Must specify date, date range, a set of appnames (e.g. org.mozilla.fennec) or a set of apks (if --use-apks is specified)")

    device_prefs = eideticker.getDevicePrefs(options)

    if appnames:
        for appname in appnames:
            runtest(device_prefs, testname, options, appname=appname)
    elif apks:
        for apk in apks:
            runtest(device_prefs, testname, options, apk=apk)
    else:
        br = eideticker.BuildRetriever()
        productname = "nightly"
        product = eideticker.get_product(productname)
        for date in dates:
            apk = br.get_build(product, date)
            runtest(device_prefs, testname, options, apk=apk, appdate=date)

main()

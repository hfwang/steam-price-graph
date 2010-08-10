# relativeDates.py by Jehiah Czebotar
# http://jehiah.com/
# released under whatever license you want; modify as you see fit

import math,time
def getRelativeTimeStr(str_time,time_format="%m/%d/%y %H%M",accuracy=1,cmp_time=None,alternative_past=None):
    # convert str_time to date
    t = time.mktime(time.strptime(str_time,time_format))
    return getRelativeTime(t,accuracy=accuracy,cmp_time=cmp_time,alternative_past=alternative_past)

def getRelativeTime(t,accuracy=1,cmp_time=None,alternative_past=None):
    if cmp_time==None:
        cmp_time = time.time()
    diff_seconds = (t - cmp_time) + 20 # unknown why it's off by 20 seconds
    diff_minutes = int(math.floor(diff_seconds/60))
    relative_time = ""

    sign = diff_minutes > 0
    diff_minutes = math.fabs(diff_minutes)
    # return in minutes
    if diff_minutes > (60 * 24):
        relative_time = str(int(math.floor(diff_minutes / (60*24)))) + " days"
        if accuracy > 1:
            relative_time +=" "+ str(int(math.floor((diff_minutes % (60*24))) / 60)) + " hours"
    elif diff_minutes > 60 :
        relative_time = str(int(math.floor(diff_minutes / 60))) + " hours"
        if accuracy > 1:
            relative_time +=" "+ str(int(diff_minutes % 60)) + " mins"
    else:
        relative_time = str(int(diff_minutes)) + " minutes"

    if sign:
        relative_time = "in " + relative_time
    else:
        if alternative_past:
            return alternative_past
        relative_time += " ago"
    return relative_time

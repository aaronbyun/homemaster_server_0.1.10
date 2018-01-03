#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

from sender.push_sender import send_24hours_ahead_notification, send_10mins_ahead_notification, send_cleaning_complete_notification, send_rating_notification

if __name__ == '__main__':
    if len(sys.argv) != 3:
        exit(-1)

    command = sys.argv[1]
    booking_id = sys.argv[2]

    devicetype = 'android'

    reg_ids = ['APA91bEAnXoBeVhU_6SBAF2GEfZYNZWF6kqpks5tJCCmxE1vLMa-R26R8y95KsBOpat0l355jGAEmPxTUGRbg34EmCUHhDCL4dlQS8lrS9Dpz7qFV7KQxNtPTkDrnLGIPC8PdNBNz2h0']

    if command == '1':
        send_new_booking_notification(reg_ids, booking_id, '21231', '1212')
    elif command == '2':
        send_10mins_ahead_notification(devicetype, reg_ids, booking_id)
    elif command == '3':
        send_cleaning_complete_notification(devicetype, reg_ids, booking_id)
    elif command == '4':
        send_rating_notification(devicetype, reg_ids, booking_id, '김진영2')
    else:
        print 'invlaid argument'



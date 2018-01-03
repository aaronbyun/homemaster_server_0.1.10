#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import datetime as dt
from data.session.mysql_session import BizSession
from data.model.data_model import EM_MMT_TRAN
from err.error_handler import print_err_detail, err_dict

try:
    from utils.secrets import ALIM_SENDER_KEY
except ImportError:
    ALIM_SENDER_KEY = ''


TEMPLATE = {}
TEMPLATE['noti_48']                 = {'code' : 'hm023', 'content' : '{}고객님, 48시간 후 홈마스터 {}님이 방문합니다. 혹시 추가사항 신청하기를 깜박하지 않으셨나요?'}
TEMPLATE['noti_24']                 = {'code' : 'hm022', 'content' : '{}고객님, 24시간 후 홈마스터 {}님이 방문합니다. 내일 뵙겠습니다^^'}
TEMPLATE['noti_10']                 = {'code' : 'hm021', 'content' : '{}고객님, 10분 후 {} 홈마스터님이 방문하여 클리닝을 시작합니다!'}
TEMPLATE['noti_complete']           = {'code' : 'hm020', 'content' : '{}고객님, 클리닝이 완료 되었습니다. 기분 좋은 하루 보내세요 ^^'}
TEMPLATE['noti_rate']               = {'code' : 'hm019', 'content' : '{}고객님, 오늘 클리닝은 어떠셨나요? {} 홈마스터님에게 평가를 남겨주세요.'}

TEMPLATE['noti_mc_request']         = {'code' : 'hm018', 'content' : '{}고객님의 예약 문의가 접수되었습니다. 담당 매니저가 30분 안으로 연락 드리겠습니다. 감사합니다^^'}
TEMPLATE['noti_mc_complete']        = {'code' : 'hm014', 'content' : '{}고객님의 예약이 완료 되었습니다.\n[예약날짜]: {}\n[예약주소]: {}\n[취소환불규정] : 당일 취소 시, 수수료 30%가 부과됩니다. 자세한 사항은 아래의 링크를 참고해주세요.\n{}'}
TEMPLATE['noti_mc_line']            = {'code' : 'hm013', 'content' : '{}고객님의 예약내역입니다. 아래 링크에서 예약을 완료 해주세요.\n{}'}

TEMPLATE['noti_caution']            = {'code' : 'hm024', 'content' : '[자주 묻는 질문]\n{}\n[서비스 범위]\n{}\n[요청사항]\n- 청소기와 쓰레기 봉투를 준비해주세요.\n- 세탁물은 미리 분류해 담아주세요.(분류되지 않은 세탁 시, 이염/손상은 책임지지 않습니다)\n- 귀중품이나 중요한 물품은 안전한 곳에 보관해주세요.\n- 파손 되었거나 파손되기 쉬운물건은 미리 말씀해주세요.\n- 버리면 안되는 물건은 미리 말씀해주세요.'}
TEMPLATE['noti_reservation']        = {'code' : 'hm016', 'content' : '{}고객님의 예약내역입니다.\n[예약날짜]: {}\n[예약주기]: {}\n[예약내용]: {}\n[상세안내]: {}'}

TEMPLATE['noti_master_tomorrow']    = {'code' : 'hm010', 'content' : '{} 홈마스터님, 내일 청소 잊지 않으셨죠?^^ 총 {}분의 고객님 클리닝 예정 입니다.\n항상 10분 전 집 앞에 도착해 주세요. 감사합니다!'}


TEMPLATE['noti_manager_rate']         = {'code' : 'hm030', 'content' : '{}고객님, {}마스터님에게 평가완료 ({}, {})'}
TEMPLATE['noti_manager_new']          = {'code' : 'hm029', 'content' : '{}고객님 예약됨({}}}'}
TEMPLATE['noti_manager_modify_task']  = {'code' : 'hm028', 'content' : '{}고객님, 추가업무 변경 {}'}
TEMPLATE['noti_manager_modify_date']  = {'code' : 'hm027', 'content' : '{}고객님, 예약 시간 변경 {}'}
TEMPLATE['noti_manager_cancel']       = {'code' : 'hm025', 'content' : '{} 고객님, 취소 {}, {}'}
TEMPLATE['noti_manager_cancel_all']   = {'code' : 'hm026', 'content' : '{} 고객님, 전체 취소 {}, {}'}

TEMPLATE['noti_manager_dayoff']       = {'code' : 'hm042', 'content' : '{}홈마스터님 휴무신청\n휴무날짜 : {}'}
TEMPLATE['noti_manager_modify_schedule'] = {'code' : 'hm041', 'content' : '{}홈마스터님 일정 변경 신청\n고객 : {}\n지역 : {}\n예약날짜 : {}'}

TEMPLATE['notify_charge_failure']                   = {'code' : 'hm070', 'content' : '[홈마스터] 미결제요금 안내\n\n고객님 미결제 요금이 확인 되었습니다.\n\n이용일시 : {}\n결제요금 : {}\n\n미결제 요금은\n매 익일 오후 2시에 자동으로 재결제 요청 됩니다.\n\n다음 클리닝 날짜 3일 전까지 결제 완료 되지 않으면 다음 클리닝은 자동으로 취소 됩니다.\n\n감사합니다.'}
TEMPLATE['notify_try_charge_unpaid_success']        = {'code' : 'hm071', 'content' : '[홈마스터] 미결제요금 안내\n\n고객님 미결제 요금이 결제 되었습니다.\n\n이용일시 : {}\n결제요금 : {}\n\n감사합니다.'}
TEMPLATE['notify_try_charge_unpaid_cancel_all']        = {'code' : 'hm072', 'content' : '[홈마스터]\n미결제요금으로 인한 클리닝 취소 안내\n\n고객님 미결제 요금이 지연되어  다음 클리닝 예약이 자동으로 취소 되었습니다.\n\n이용일시 : {}\n결제요금 : {}\n\n미결제 요금은\n매 익일 오후 2시에 자동으로 재결제 요청 됩니다.\n\n감사합니다.'}

def upload_alimtalk_content(template_code, content, recipient_num):
    try:
        now = dt.datetime.now()
        session = BizSession()
        message = EM_MMT_TRAN(date_client_req = now,
                          template_code = template_code,
                          content = content,
                          recipient_num = recipient_num,
                          msg_status = '1',
                          subject = ' ',
                          callback = '',
                          sender_key = ALIM_SENDER_KEY,
                          service_type = '3',
                          msg_type = '1008')

        session.add(message)
        session.commit()
    except Exception, e:
        session.rollback()
        print_err_detail(e)
    finally:
        session.close()


def send_alimtalk(to, alim_code, *args):
    recipient_num = to

    try:
        template_code = TEMPLATE[alim_code]['code']
        content       = TEMPLATE[alim_code]['content']
    except Exception, e:
        print 'No alimcode', alim_code
        return False

    content = content.format(*args)
    print content
    upload_alimtalk_content(template_code, content, recipient_num)


if __name__ == '__main__':
    '''send_alimtalk('01034576360', 'noti_48',               '변영효', '김영임')
    send_alimtalk('01034576360', 'noti_24',               '변영효', '김영임')
    send_alimtalk('01034576360', 'noti_10',               '변영효', '김영임')
    send_alimtalk('01034576360', 'noti_complete',         '변영효')
    send_alimtalk('01034576360', 'noti_mc_request',       '변영효')
    send_alimtalk('01034576360', 'noti_mc_complete',      '변영효', '2016년 3월 20일', '경기도 성남시 분당구 판교로 20 301-101', 'http://homemaster.co.kr')
    send_alimtalk('01034576360', 'noti_mc_line',          '변영효', 'http://homemaster.co.kr')
    send_alimtalk('01034576360', 'noti_caution',          'http://homemaster.co.kr', 'http://homemaster.co.kr', )
    send_alimtalk('01034576360', 'noti_reservation',      '변영효', '2016년 3월 20일 금요일 오전 9시0분', '2주 1회', '기본클리닝, 창문창틀', 'http://goo.gl/j6PByf')'''

    send_alimtalk('01034576360', 'noti_master_tomorrow',  '김잔듸', '3')
    send_alimtalk('01034576360', 'noti_manager_dayoff', '변영효', '2016-06-20')
    send_alimtalk('01034576360', 'noti_manager_modify_schedule', '변영효', '마이클 조던', '강남구', '2016-06-20')

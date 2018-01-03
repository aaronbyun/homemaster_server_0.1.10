#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, CHAR, Date, String, Time, Index, DateTime, TIMESTAMP, func
from sqlalchemy.dialects.mysql import INTEGER, BIT, TINYINT, TIME, DOUBLE, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import PrimaryKeyConstraint
from data.config.mysql_config import get_connection_string

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id              = Column(CHAR(36), primary_key = True, nullable = False)
    name            = Column(String(64), nullable = False, index = True)
    gender          = Column(Integer, default = 0)
    authsource      = Column(String(20), nullable = False, default = 'None')
    devicetype      = Column(String(15), nullable = False, default = 'normal')
    email           = Column(String(96), nullable = False, unique = True)
    password        = Column(String(256), nullable = False)
    salt            = Column(CHAR(128), nullable = False,)
    phone           = Column(String(64), nullable = False)
    dateofbirth     = Column(String(64), nullable = True, default = None)
    dateofreg       = Column(DateTime, nullable = True, default = None)
    dateoflastlogin = Column(DateTime, nullable = False)
    active          = Column(Integer, nullable = False, default = 1)
    is_b2b          = Column(Integer, nullable = False, default = 0)

class UserAddress(Base):
    __tablename__ = 'user_addresses'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id             = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    address             = Column(String(256), nullable = False)
    size                = Column(Integer, nullable = False)
    kind                = Column(Integer, nullable = False)
    rooms               = Column(Integer, nullable = False, default = 0)
    baths               = Column(Integer, nullable = False, default = 0)
    user_addr_index     = Column(Integer, nullable = False)
    latitude            = Column(DOUBLE, nullable = False)
    longitude           = Column(DOUBLE, nullable = False)
    geohash5            = Column(String(5), nullable = False)
    geohash6            = Column(String(6), nullable = False)

    user                = relationship(User)

class UserDefaultAddress(Base):
    __tablename__ = 'user_default_addresses'

    user_id     = Column(CHAR(36), ForeignKey('user_addresses.user_id'), primary_key = True,  nullable = False, unique = True, index = True)
    address_idx = Column(Integer, nullable = False)

    useraddress = relationship(UserAddress)


class UserCard(Base):
    __tablename__ = 'user_cards'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id         = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    billkey         = Column(String(32), nullable = False)
    card_alias      = Column(String(36), nullable = False)
    auth_date       = Column(Date, nullable = False)
    user_card_index = Column(Integer, nullable = False)

    user            = relationship(User)


class UserDefaultCard(Base):
    __tablename__ = 'user_default_cards'

    user_id     = Column(CHAR(36), ForeignKey('user_cards.user_id'), primary_key = True,  nullable = False, unique = True, index = True)
    card_idx = Column(Integer, nullable = False)

    usercard    = relationship(UserCard)


class UserPaymentRecord(Base):
    __tablename__ = 'user_payment_records'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    tid             = Column(String(30), primary_key = True, nullable = False, unique = True, index = True)
    booking_id      = Column(String(16), nullable = False, index = True)
    user_id         = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    price           = Column(Integer, nullable = False)
    auth_date       = Column(String(15), nullable = False)
    canceled_amount = Column(Integer, nullable = False, default = 0)
    canceled_date   = Column(String(15), nullable = True, default = None)
    status          = Column(String(20), nullable = False)

    user            = relationship(User)


class UserPaymentRecordForIOS(Base):
    __tablename__ = 'user_payment_records_for_ios'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id      = Column(String(16), nullable = False, index = True)
    user_id         = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    amount          = Column(Integer, nullable = False)
    datetime        = Column(DateTime, nullable = False)

    user            = relationship(User)


class ManualPaymentRecord(Base):
    __tablename__ = 'manual_payment_records'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id         = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    amount          = Column(Integer, nullable = False)
    auth_date       = Column(String(15), nullable = False)
    interest        = Column(String(8), nullable = True, default = '1')
    quota           = Column(String(8), nullable = True, default = '00')

    user = relationship(User)


class UserChargeRecord(Base):
    __tablename__ = 'user_charge_under2month_records'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    tid             = Column(String(30), primary_key = True, nullable = False, unique = True, index = True)
    user_id         = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    amount          = Column(Integer, nullable = False)
    auth_date       = Column(String(15), nullable = False)

    user            = relationship(User)


class UserPushKey(Base):
    __tablename__ = 'user_pushkey'

    id          = Column(Integer, primary_key = True, nullable = True, autoincrement = True)
    user_id     = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    pushkey     = Column(String(256), nullable = False)

    user            = relationship(User)


class UserMemo(Base):
    __tablename__ = 'user_memos'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id             = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    memo                = Column(TEXT, nullable = False)
    requested_datetime  = Column(DateTime, nullable = False)
    processed_datetime  = Column(DateTime, default = None)
    response            = Column(String(191), default = None)

    user            = relationship(User)

class UserFreeEvent(Base):
    __tablename__ = 'user_free_event'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_request_id  = Column(CHAR(36), nullable = False)
    user_id             = Column(CHAR(36), nullable = False)
    datetime            = Column(DateTime, nullable = False)


class UserCoupon(Base):
    __tablename__ = 'user_coupons'
    id                  = Column(String(8), primary_key = True, nullable = False)
    user_id             = Column(CHAR(36), nullable = False, index = True)
    booking_id          = Column(String(16), nullable = False, index = True)
    expire_date         = Column(DateTime, nullable = False)
    used                = Column(Integer, nullable = False, default = 0)
    discount_price      = Column(Integer, nullable = False, default = 0)
    service_price       = Column(Integer, nullable = False, default = 0)
    used_datetime       = Column(DateTime, nullable = False)
    description         = Column(String(100), nullable = False, default = None)
    title               = Column(String(50), default = None)
    issue_date          = Column(DateTime, default = None)

class UserReason(Base):
    __tablename__ = 'user_reasons'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id             = Column(CHAR(36), nullable = False, index = True)
    contact1            = Column(CHAR(150), nullable = True)
    contact2            = Column(CHAR(150), nullable = True)
    contact3            = Column(CHAR(150), nullable = True)
    contact1_time       = Column(DateTime, nullable = True)
    contact2_time       = Column(DateTime, nullable = True)
    contact3_time       = Column(DateTime, nullable = True)
    reason              = Column(TEXT, nullable = False)
    status              = Column(CHAR(20), nullable = False)
    possible            = Column(CHAR(20), nullable = False)

class WaitingUser(Base):
    __tablename__ = 'waiting_users'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id     = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    sido_id     = Column(Integer, nullable = False, index = True)
    sigungu_id  = Column(Integer, nullable = False, index = True)

    user            = relationship(User)


class RejectRelation(Base):
    __tablename__ = 'reject_relation'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id     = Column(CHAR(36), nullable = False, index = True)
    master_id   = Column(CHAR(36), nullable = False, index = True)


class Manager(Base):
    __tablename__ = 'managers'
    id      = Column(CHAR(36), primary_key = True, nullable = False)
    name    = Column(String(45), nullable = False, index = True)
    phone   = Column(String(30), nullable = False)


class Master(Base):
    __tablename__ = 'masters'

    id          = Column(CHAR(36), primary_key = True, nullable = False)
    manager_id  = Column(CHAR(36), ForeignKey('managers.id'), nullable = False)
    name        = Column(String(45), nullable = False, index = True)
    email       = Column(String(100), nullable = False, unique = True)
    level       = Column(Integer, nullable = False)
    cardinal    = Column(Integer, nullable = False)
    age         = Column(Integer, nullable = False)
    gender      = Column(Integer, nullable = False)
    img_url     = Column(String(200), unique = True, default = None)
    password    = Column(String(256), nullable = False)
    salt        = Column(CHAR(128), nullable = False,)
    phone       = Column(String(30), nullable = False)
    address     = Column(String(250), nullable = False)
    pet_alergy  = Column(Integer, nullable = False, default = 0)
    need_route  = Column(Integer, nullable = False, default = 0)
    another_job = Column(Integer, nullable = False, default = 0)
    t_size      = Column(String(4), nullable = False, default = 'M')
    feedback    = Column(String(100))
    message     = Column(String(100))
    active      = Column(Integer, nullable = False, default = 1)
    dateofreg   = Column(Date, nullable = True, default = None)

    manager     = relationship(Manager)

class MasterNotice(Base):
    __tablename__ = 'master_notices'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    title       = Column(String(191), nullable = True, default = None)
    content     = Column(TEXT, nullable = True, default = None)
    reg_time    = Column(DateTime, nullable = False)
    active      = Column(Integer, nullable = False, default = 1)

class MasterAccount(Base):
    __tablename__ = 'master_accounts'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id   = Column(CHAR(36), nullable = False, index = True)
    account_no  = Column(String(100), nullable = False)
    bank_code   = Column(Integer, nullable = False)
    bank_name   = Column(String(30), nullable = False)
    datetime    = Column(DateTime, nullable = False)


class MasterSalary(Base):
    __tablename__ = 'master_salaries'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id   = Column(CHAR(36), ForeignKey('masters.id'), primary_key = True,  nullable = False)
    amount      = Column(Integer, nullable = False)
    grant_date  = Column(DateTime, nullable = False)

    master      = relationship(Master)

class MasterDeficiency(Base):
    __tablename__ = 'master_deficiencies'

    id      = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    gu_id   = Column(Integer, nullable = False)
    user_id = Column(Integer, nullable = False)

class BlockUser(Base):
    __tablename__ = 'block_users'

    id      = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id = Column(Integer, nullable = False)

class EduYoutubeMovie(Base):
    __tablename__ = 'edu_youtube_movies'

    id      = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    content = Column(CHAR(36), nullable = False)
    description = Column(String(100), nullable = True, default = None)

class MasterScheduleByDate(Base):
    __tablename__ = 'master_schedules_by_date'

    master_id   = Column(CHAR(36), ForeignKey('masters.id'), primary_key = True,  nullable = False)
    date        = Column(Date, primary_key = True, nullable = False)
    free_from   = Column(Time, nullable = False)
    free_to     = Column(Time, nullable = False)
    active      = Column(Integer, nullable = False, default = 1)

    master      = relationship(Master)

class MasterPushKey(Base):
    __tablename__ = 'master_pushkey'

    id          = Column(Integer, primary_key = True, nullable = True, autoincrement = True)
    master_id   = Column(CHAR(36), ForeignKey('masters.id'), nullable = False, index = True)
    pushkey     = Column(String(256), nullable = False)

    master            = relationship(Master)


class MasterTimeSlot(Base):
    __tablename__ = 'master_timeslots'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id   = Column(CHAR(36), ForeignKey('masters.id'), nullable = False, index = True)
    day_of_week = Column(TINYINT(3), nullable = False)
    start_time  = Column(Time, nullable = False)
    end_time    = Column(Time, nullable = False)

    master      = relationship(Master)

class MasterPreferedArea(Base):
    __tablename__ = 'master_prefered_area'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id       = Column(CHAR(36), ForeignKey('masters.id'), nullable = False, index = True)
    prefered_gu     = Column(Integer, nullable = False, index = True)

    master      = relationship(Master)


class MasterPointDescription(Base):
    __tablename__ = 'master_point_description'

    index       = Column(Integer, primary_key = True, nullable = False)
    description = Column(String, nullable = False)
    point       = Column(Integer, nullable = False, default = 0)


class MasterPoint(Base):
    __tablename__ = 'master_point'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id       = Column(CHAR(36), ForeignKey('masters.id'), nullable = False, index = True)
    point_index     = Column(Integer, ForeignKey('master_point_description.index'), nullable = False, default = 0)
    point           = Column(Integer, nullable = False, default = 0)
    point_date      = Column(DateTime, nullable = False)

    master      = relationship(Master)
    master_point_description = relationship(MasterPointDescription)


class MasterPrize(Base):
    __tablename__ = 'master_prize'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id           = Column(CHAR(36), nullable = False, index = True)
    prize               = Column(Integer, nullable = False, default = 0)
    prize_description   = Column(String(255), nullable = False, default = '')
    earn_date           = Column(DateTime, nullable = False)


class MasterPenalty(Base):
    __tablename__ = 'master_penalty'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id           = Column(CHAR(36), nullable = False, index = True)
    category_idx        = Column(Integer, nullable = False, default = 0)
    penalty_idx         = Column(Integer, nullable = False, default = 0)
    penalty             = Column(String(255), nullable = True)
    penalty_date        = Column(DateTime, nullable = False)


class MasterMemo(Base):
    __tablename__ = 'master_memos'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id             = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    master_id           = Column(CHAR(36), ForeignKey('masters.id'), nullable = False, index = True)
    memo                = Column(TEXT, nullable = False)
    datetime            = Column(DateTime, nullable = False)

    user        = relationship(User)
    master      = relationship(Master)


class MasterClaim(Base):
    __tablename__ = 'master_claims'

    id                  = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id           = Column(CHAR(36), nullable = False, index = True)
    user_id             = Column(CHAR(36), nullable = False, index = True)
    claim_text          = Column(TEXT, nullable = False)
    register_time       = Column(DateTime, nullable = False)


class MasterBookingModifyRequest(Base):
    __tablename__ = 'master_booking_modify_requests'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id       = Column(CHAR(36), nullable = False, index = True)
    booking_id      = Column(String(16), nullable = False, index = True)
    reason          = Column(TEXT, nullable = False)
    org_time        = Column(DateTime, nullable = True)
    request_time    = Column(DateTime, nullable = False)


class MasterDayoffRequest(Base):
    __tablename__ = 'master_day_off_requests'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    master_id       = Column(CHAR(36), nullable = False, index = True)
    date            = Column(Date, nullable = False, index = True)
    type            = Column(Integer, nullable = False) # 0 - cancel, 1 - request
    request_time    = Column(DateTime, nullable = False)


class RegularBasisManagement(Base):
    __tablename__ = 'regular_basis_management'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id      = Column(CHAR(16), nullable = False)
    try_1st         = Column(String(20), nullable = False)
    try_2nd         = Column(String(20), nullable = False)
    try_3rd         = Column(String(20), nullable = False)
    memo            = Column(TEXT, nullable = True)


class Order11st(Base):
    __tablename__ = 'order_11st'

    order_id = Column(String(30), primary_key = True, nullable = False)


class OrderID11st(Base):

    __tablename__ = '11st_order_ids'

    booking_id  = Column(String(16), primary_key = True, nullable = False)
    div_no      = Column(String(50), primary_key = True, nullable = False)
    datetime    = Column(DateTime, nullable = False)


class Booking(Base):
    __tablename__ = 'bookings'

    id                  = Column(String(16), primary_key = True, nullable = False)
    request_id          = Column(CHAR(36), nullable = False, index = True)
    master_id           = Column(CHAR(36), ForeignKey('masters.id'), nullable = True, index = True, default = None)
    user_id             = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    appointment_type    = Column(Integer, nullable = False)
    appointment_index   = Column(Integer, nullable = False)
    dow                 = Column(Integer, nullable = False)
    booking_time        = Column(DateTime, default = None)
    org_start_time      = Column(DateTime, default = None)
    start_time          = Column(DateTime, default = None)
    working_start_time  = Column(DateTime, default = None)
    estimated_end_time  = Column(DateTime, nullable = False)
    end_time            = Column(DateTime, nullable = False, default = -1)
    cleaning_duration   = Column(Integer, default = 0)
    additional_task     = Column(Integer, default = 0)
    price               = Column(Integer, nullable = False)
    price_with_task     = Column(Integer, nullable = False)
    vat                 = Column(Integer, default = 0)
    charging_price      = Column(Integer, default = -1)
    tid                 = Column(String(30), default = None)
    card_idx            = Column(Integer, nullable = False)
    addr_idx            = Column(Integer, nullable = False)
    message             = Column(TEXT, default = None)
    trash_location      = Column(String(256), default = None)
    enterhome           = Column(TEXT, default = None)
    enterbuilding       = Column(TEXT, default = None)
    routing_method      = Column(TEXT, default = None)
    havetools           = Column(Integer, nullable = False, default = 0)
    havepet             = Column(Integer, nullable = False, default = 0)
    laundry_apply_all   = Column(Integer, nullable = False, default = 0)
    master_gender       = Column(Integer, nullable = False, default = 0)
    havereview          = Column(Integer, nullable = False, default = 0)
    is_dirty            = Column(Integer, nullable = False, default = 0)
    is_master_changed   = Column(Integer, nullable = False, default = 0)
    source              = Column(String(20), nullable = False, default = 'hm')
    user_type           = Column(String(45), nullable = False, default = 'unknown')
    wage_per_hour       = Column(Integer, nullable = False, default = 0)
    status              = Column(Integer, nullable = False)
    cleaning_status     = Column(Integer, nullable = False, default = 0)
    payment_status      = Column(Integer, nullable = False, default = 0)

    master              = relationship(Master)
    user                = relationship(User)


class MovingCleaningBooking(Base):
    __tablename__ = 'moving_cleaning_bookings'

    id               = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id          = Column(CHAR(36), ForeignKey('users.id'), nullable = False, index = True)
    addr_idx         = Column(Integer, nullable = False, default = 0)
    datetime         = Column(DateTime, nullable = False)

    user                = relationship(User)

class Promotion(Base):
    __tablename__ = 'promotions'

    promotion_code = Column(String(12), primary_key = True, nullable = False, unique = True)
    booking_id     = Column(String(16), ForeignKey('bookings.id'), nullable = True, default = None)
    used           = Column(Integer, nullable = False, default = 0)
    discount_price = Column(Integer, nullable = False, default = 5000)
    service_price  = Column(Integer, nullable = False, default = 0)
    used_datetime  = Column(DateTime, nullable = True)
    source         = Column(String(10), nullable = False, default = 'hm')

    bookings        = relationship(Booking)


class EventPromotionBooking(Base):
    __tablename__ = 'event_promotion_bookings'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id      = Column(String(16), nullable = False)
    event_name      = Column(String(45), nullable = False)
    discount_price  = Column(Integer, nullable = False, default = 0)


class EventPromotion(Base):
    __tablename__ = 'event_promotions'

    code = Column(String(5), primary_key = True, nullable = False)
    amount = Column(Integer, nullable = False, default = 5000)
    count = Column(Integer, nullable = False, default = 1000)
    expires = Column(DateTime, nullable = False)


class Rating(Base):
    __tablename__ = 'ratings'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id      = Column(String(16), ForeignKey('bookings.id'), nullable = False, index = True)
    master_id       = Column(CHAR(36), ForeignKey('masters.id'), nullable = True, index = True)
    rate_clean      = Column(DOUBLE, nullable = False)
    review_clean    = Column(TEXT, nullable = False)
    rate_master     = Column(DOUBLE, nullable = False)
    review_master   = Column(TEXT, nullable = False)
    review_time     = Column(DateTime, default = None)

    bookings        = relationship(Booking)
    masters         = relationship(Master)

class CancelReason(Base):
    __tablename__ = 'cancel_reasons'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id      = Column(String(16), ForeignKey('bookings.id'), nullable = False, index = True)
    user_id         = Column(CHAR(36), ForeignKey('users.id'), nullable = True, index = True)
    reason_id       = Column(Integer, nullable = False, default = 0)
    etc_reason      = Column(String(100), default = None)
    kind            = Column(Integer, nullable = False, default = 0) # 0 - cancel, 1 - cancel all
    cancel_time     = Column(DateTime, nullable = True, default = None)


class Sido(Base):
    __tablename__ = 'sido'

    id      = Column(Integer, primary_key = True, nullable = False)
    name    = Column(String(15), nullable = False)


class Sigungu(Base):
    __tablename__ = 'sigungu'

    id      = Column(Integer, primary_key = True, nullable = False)
    sido_id = Column(Integer, ForeignKey('sido.id'), nullable = False, index = True)
    name    = Column(String(15), nullable = False)

    sido    = relationship(Sido)


class JibunAddress(Base):
    __tablename__ = 'jibun_address'

    dong_code               = Column(String(10), nullable = False)
    sido                    = Column(String(20), nullable = False, index = True)
    sigungu                 = Column(String(20), nullable = False, index = True)
    dong                    = Column(String(20), nullable = False, index = True)
    ri                      = Column(String(20), default = None)
    san                     = Column(String(1), default = None)
    beonji                  = Column(Integer, default = 0)
    ho                      = Column(Integer, default = 0)
    doro_code               = Column(String(12), primary_key = True,  nullable = False, index = True)
    jiha                    = Column(String(1), primary_key = True, default = None)
    b_main_no               = Column(Integer, primary_key = True, nullable = False)
    b_minor_no              = Column(Integer, primary_key = True, default = 0)
    jibun_serial            = Column(String(10), primary_key = True, nullable = False)
    modification_code       = Column(String(2), default = None)

    __table_args__ = (PrimaryKeyConstraint(doro_code, jiha, b_main_no, b_minor_no, jibun_serial),{})


class Version(Base):
    __tablename__ = 'versions'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    major       = Column(Integer, nullable = False)
    minor       = Column(Integer, nullable = False)
    patch       = Column(Integer, nullable = False)
    mandatory   = Column(Integer, nullable = False, default = 0)
    description = Column(String(100), nullable = True, default = None)


class UserClaim(Base):
    __tablename__ = 'user_claims'

    id            = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id    = Column(String(16), ForeignKey('bookings.id'), nullable = False, index = True)
    comment       = Column(TEXT, nullable = False)
    register_time = Column(DateTime, nullable = False)

class AdminMemo(Base):
    __tablename__ = 'admin_memos'

    id            = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    user_id       = Column(CHAR(36), ForeignKey('users.id'), nullable = True, index = True)
    memo          = Column(TEXT, nullable = False)
    register_time = Column(DateTime, nullable = False)

class IOSVersion(Base):
    __tablename__ = 'ios_versions'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    major       = Column(Integer, nullable = False)
    minor       = Column(Integer, nullable = False)
    patch       = Column(Integer, nullable = False)
    mandatory   = Column(Integer, nullable = False, default = 0)
    description = Column(String(100), nullable = True, default = None)


class MasterVersion(Base):
    __tablename__ = 'versions_master'

    id          = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    major       = Column(Integer, nullable = False)
    minor       = Column(Integer, nullable = False)
    patch       = Column(Integer, nullable = False)
    mandatory   = Column(Integer, nullable = False, default = 0)
    description = Column(String(100), nullable = True, default = None)

class HomemasterEvent(Base):
    __tablename__ = 'homemaster_events'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    title           = Column(String(100), nullable = False)
    description     = Column(String(100), nullable = True)
    image_url_mo    = Column(String(100), nullable = False)
    image_url_web   = Column(String(100), nullable = False)
    link            = Column(String(150), nullable = False)
    post_date       = Column(DateTime, nullable = False)
    expire_date     = Column(DateTime, nullable = False)


class ExtraTime(Base):
    __tablename__ = 'extra_times'

    id              = Column(Integer, primary_key = True, nullable = False, autoincrement = True)
    booking_id      = Column(String(16), nullable = False)
    extended_mins   = Column(Integer, nullable = False)
    request_time    = Column(DateTime, nullable = False)


class DoroAddress(Base):
    __tablename__ = 'doro_address'

    dong_code               = Column(String(10), nullable = False)
    sido                    = Column(String(20), nullable = False, index = True)
    sigungu                 = Column(String(20), nullable = False, index = True)
    dong                    = Column(String(20), nullable = False, index = True)
    ri                      = Column(String(20), default = None)
    san                     = Column(String(1), default = None)
    beonji                  = Column(Integer, default = 0)
    ho                      = Column(Integer, default = 0)
    doro_code               = Column(String(12), nullable = False, index = True)
    doro_name               = Column(String(80), nullable = False)
    jiha                    = Column(String(1), default = None)
    b_main_no               = Column(Integer, nullable = False)
    b_minor_no              = Column(Integer, default = 0)
    building_name           = Column(String(40), default = None)
    long_building_name      = Column(String(100), default = None)
    building_no             = Column(String(25), primary_key = True, nullable = False)
    dong_serial             = Column(String(2), default = None)
    ad_dong_code            = Column(String(10), default = None)
    ad_dong_name            = Column(String(20), default = None)
    zipcode                 = Column(String(6), nullable = False)
    zipserial               = Column(String(3), default = None)
    delivery_name           = Column(String(40), default = None)
    modification_code       = Column(String(2), default = None)
    date_posted             = Column(String(8), default = None)
    former_address          = Column(String(25), default = None)
    sigungu_building_name   = Column(String(200), default = None)
    share                   = Column(String(1), default = None)
    basic_district_num      = Column(String(5), default = None)
    has_detailed            = Column(String(1), default = None)
    extra1                  = Column(String(5), default = None)
    extra2                  = Column(String(5), default = None)

    __table_args__ = (Index('DoroAddress_searchbyjibun_idx1', 'sido', 'dong', 'beonji', 'ho'),
                      Index('DoroAddress_searchbyjibun_idx2', 'sido', 'ad_dong_name', 'beonji', 'ho'),
                      Index('DoroAddress_searchbydoro_idx1', 'sido', 'doro_name', 'b_main_no', 'b_minor_no'))


class EM_MMT_TRAN(Base):
    __tablename__ = 'em_mmt_tran'

    mt_pr                   = Column(Integer,   nullable = False, primary_key = True, autoincrement = True)
    mt_refkey               = Column(String(20))
    priority                = Column(CHAR(2),   nullable = False, default = 'S')
    msg_class               = Column(CHAR(1),                     default = '1')
    date_client_req         = Column(DateTime,  nullable = False)
    subject                 = Column(String(40), nullable = False)
    content_type            = Column(Integer, default = 0)
    content                 = Column(String(4000), nullable = False)
    attach_file_group_key   = Column(Integer, default = 0)
    callback                = Column(String(25), nullable = False)
    service_type            = Column(CHAR(2), nullable = False, default = '3')
    broadcast_yn            = Column(CHAR(1), nullable = False, default = 'N')
    msg_status              = Column(CHAR(1), nullable = False, default = '1')
    recipient_num           = Column(String(25))
    date_mt_sent            = Column(DateTime)
    date_rslt               = Column(DateTime)
    date_mt_report          = Column(DateTime)
    mt_report_code_ib       = Column(CHAR(4))
    mt_report_code_ibtype   = Column(CHAR(1))
    carrier                 = Column(Integer)
    rs_id                   = Column(String(20))
    recipient_net           = Column(Integer)
    recipient_npsend        = Column(CHAR(1))
    country_code            = Column(String(8), nullable = False, default = '82')
    charset                 = Column(String(20))
    msg_type                = Column(Integer, nullable = False, default = '1008')
    crypto_yn               = Column(CHAR(1), default = 'Y')
    ttl                     = Column(Integer)
    ata_id                  = Column(CHAR(2), default = ' ')
    reg_date                = Column(TIMESTAMP, default = func.current_timestamp())
    mt_res_cnt              = Column(Integer)
    sender_key              = Column(String(40), nullable = False)
    template_code           = Column(String(10), nullable = False)
    etc_text_1              = Column(String(100))
    etc_text_2              = Column(String(100))
    etc_text_3              = Column(String(100))
    etc_num_1               = Column(Integer)
    etc_num_2               = Column(Integer)
    etc_num_3               = Column(Integer)
    etc_date_1              = Column(DateTime)

    __table_args__ = (Index('ix_em_mmt_tran_01', 'msg_status', 'date_client_req'),
                      Index('ix_em_mmt_tran_02', 'recipient_num'),
                      Index('ix_em_mmt_tran_03', 'attach_file_group_key'),
                      Index('ix_em_mmt_tran_04', 'ata_id'),
                      Index('ix_em_mmt_tran_05', 'sender_key', 'template_code'))




if __name__ == '__main__':
    pass
    #engine = create_engine(get_connection_string())

    # create all
    #Base.metadata.create_all(engine)

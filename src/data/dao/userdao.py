#-*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append('./..')
sys.path.append('../..')

import datetime as dt

from sqlalchemy import and_, or_, func, desc
from rest.booking import booking_constant as BC
from err.error_handler import print_err_detail
from data.session.mysql_session import engine, Session
from data.model.data_model import Booking, User, UserAddress, UserDefaultAddress, UserDefaultCard, RejectRelation
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from data.encryption import aes_helper as aes
from utils.geo_utils import get_latlng_from_address, get_geohash

class UserDAO(object):
    def __init__(self):
        pass

    def is_b2b(self, uid):
        is_b2b = 0
        try:
            session = Session()
            row = session.query(User).filter(User.id == uid).one()
            is_b2b = row.is_b2b

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return is_b2b

    def get_user_auth_source(self, uid):
        authsource = 'None'
        try:
            session = Session()
            row = session.query(User).filter(User.id == uid).one()
            authsource = row.authsource

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return authsource

    def get_user_device_type(self, uid):
        devicetype = ''
        try:
            session = Session()
            row = session.query(User).filter(User.id == uid).one()
            devicetype = row.devicetype

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return devicetype


    def set_user_device_type(self, uid, new_device_type):
        devicetype = ''
        try:
            session = Session()
            row = session.query(User).filter(User.id == uid).one()
            row.devicetype = new_device_type
            session.commit()

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()


    def get_user_salt(self, email):
        salt = ''
        try:
            session = Session()
            row = session.query(User).filter(User.email == email).one()
            salt = row.salt

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return salt

    def get_user_salt_by_id(self, uid):
        salt = ''
        try:
            session = Session()
            row = session.query(User).filter(User.id == uid).one()
            salt = row.salt

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return salt

    def get_user_default_address_index(self, uid):
        addr_idx = 0
        try:
            session = Session()
            row = session.query(UserDefaultAddress).filter(UserDefaultAddress.user_id == uid).one()
            addr_idx = row.address_idx

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return addr_idx

    def get_user_default_card_index(self, uid):
        card_idx = 0
        try:
            session = Session()
            row = session.query(UserDefaultCard).filter(UserDefaultCard.user_id == uid).one()
            card_idx = row.card_idx

        except NoResultFound, e:
            print_err_detail(e)
            card_idx = -1

        except MultipleResultsFound, e:
            print_err_detail(e)
            card_idx = 0

        finally:
            session.close()
            return card_idx


    def get_user_schedule_on_dates(self, uid, date_list):
        count = 0
        try:
            session = Session()

            # get default address index
            address_row = session.query(UserDefaultAddress).filter(UserDefaultAddress.user_id == uid).one()
            address_idx = address_row.address_idx

            cond = or_(*[func.date(Booking.start_time) == date for date in date_list])
            count = session.query(Booking).filter(Booking.user_id == uid) \
                        .filter(Booking.cleaning_status == BC.BOOKING_UPCOMMING) \
                        .filter(Booking.addr_idx == address_idx) \
                        .filter(cond) \
                        .count()
        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()
            return count


    def get_user_name(self, uid):
        name = ''
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User).filter(User.id == uid).one()
            name = crypto.decodeAES(row.name)
        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return name


    def get_user_phone(self, uid):
        phone = ''
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User).filter(User.id == uid).one()
            phone = crypto.decodeAES(row.phone)
        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        finally:
            session.close()
            return phone


    def get_user_address_detail(self, uid):
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User, UserAddress) \
                .join(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                .join(UserAddress, and_(User.id == UserAddress.user_id, UserAddress.user_addr_index == UserDefaultAddress.address_idx)) \
                .filter(User.id == uid) \
                .one()

            address = crypto.decodeAES(row.UserAddress.address)
            size = row.UserAddress.size
            kind = row.UserAddress.kind

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return address, size, kind


    def get_user_address(self, uid):
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User, UserAddress) \
                .join(UserDefaultAddress, User.id == UserDefaultAddress.user_id) \
                .join(UserAddress, and_(User.id == UserAddress.user_id, UserAddress.user_addr_index == UserDefaultAddress.address_idx)) \
                .filter(User.id == uid) \
                .one()

            address = crypto.decodeAES(row.UserAddress.address)
            geohash5 = row.UserAddress.geohash5
            geohash6 = row.UserAddress.geohash6

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return address, geohash5, geohash6

    def get_user_address_detail_by_index(self, uid, addr_idx):
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User, UserAddress) \
                .join(UserAddress, and_(User.id == UserAddress.user_id, UserAddress.user_addr_index == addr_idx)) \
                .filter(User.id == uid) \
                .one()

            address = crypto.decodeAES(row.UserAddress.address)
            size = row.UserAddress.size
            kind = row.UserAddress.kind

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return address, size, kind

    def get_user_address_full_detail_by_index(self, uid, addr_idx):
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User, UserAddress) \
                .join(UserAddress, and_(User.id == UserAddress.user_id, UserAddress.user_addr_index == addr_idx)) \
                .filter(User.id == uid) \
                .one()

            address = crypto.decodeAES(row.UserAddress.address)
            size = row.UserAddress.size
            kind = row.UserAddress.kind
            rooms = row.UserAddress.rooms
            baths = row.UserAddress.baths

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return address, size, kind, rooms, baths

    def get_user_address_by_index(self, uid, addr_idx):
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            row = session.query(User, UserAddress) \
                .join(UserAddress, and_(User.id == UserAddress.user_id, UserAddress.user_addr_index == addr_idx)) \
                .filter(User.id == uid) \
                .one()

            address = crypto.decodeAES(row.UserAddress.address)
            geohash5 = row.UserAddress.geohash5
            geohash6 = row.UserAddress.geohash6

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return address, geohash5, geohash6


    def get_all_user_addresses(self, uid):
        addresses = []
        try:
            session = Session()

            key = self.get_user_salt_by_id(uid)[:16]
            crypto = aes.MyCrypto(key)

            result = session.query(User, UserAddress) \
                .join(UserAddress, User.id == UserAddress.user_id) \
                .filter(User.id == uid) \
                .order_by(UserAddress.user_addr_index) \
                .all()

            for row in result:
                address = crypto.decodeAES(row.UserAddress.address)
                kind = row.UserAddress.kind
                size = row.UserAddress.size

                addresses.append((address, kind, size))

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return addresses

    def find_masters_in_charge(self, uid):
        try:
            session = Session()
            result = session.query(Booking) \
                            .filter(Booking.user_id == uid) \
                            .order_by(Booking.user_id) \
                            .all()

            master_ids = []
            for row in result:
                master_ids.append(row.master_id)

            return master_ids

        except Exception, e:
            print_err_detail(e)
            return []

    def get_blocked_masters(self, uid):
        masters = []

        try:
            session = Session()
            result = session.query(RejectRelation) \
                            .filter(RejectRelation.user_id == uid) \
                            .all()

            for row in result:
                masters.append(row.master_id)

            return masters

        except Exception, e:
            print_err_detail(e)
            return []

    def add_new_address(self, user_id, address, size, kind, rooms = 0, baths = 0):
        try:
            session = Session()

            latlng = get_latlng_from_address(address)
            if len(latlng) > 1:
                latitude = latlng[0]
                longitude = latlng[1]

                geohash5 = get_geohash(latitude, longitude, 5)
                geohash6 = get_geohash(latitude, longitude, 6)
            else:
                latitude = 0.0
                longitude = 0.0
                geohash5 = ''
                geohash6 = ''

            key = self.get_user_salt_by_id(user_id)[:16]
            crypto = aes.MyCrypto(key)

            encrypted_address = crypto.encodeAES(str(address))

            count = session.query(UserAddress).filter(UserAddress.user_id == user_id) \
                            .count()
            last_index = session.query(UserAddress).filter(UserAddress.user_id == user_id) \
                        .order_by(desc(UserAddress.user_addr_index)).first()

            index = 0
            if last_index != None:
                index = last_index.user_addr_index + 1

            new_address = UserAddress(user_id = user_id, address = encrypted_address,
                                        size = size, kind = kind,
                                        rooms = rooms, baths = baths,
                                        user_addr_index = index, latitude = latitude,
                                        longitude = longitude,
                                        geohash5 = geohash5, geohash6 = geohash6)
            session.add(new_address)
            session.commit()

            # set default address index
            if count == 0:
                new_default_address = UserDefaultAddress(user_id=user_id, address_idx=index)
                session.add(new_default_address)
            else:
                record = session.query(UserDefaultAddress) \
                                .filter(UserDefaultAddress.user_id == user_id) \
                                .one()
                record.address_idx = index

            session.commit()

            return index

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

    def get_user_house_type_size(self, booking_id):

        house_type = ''
        size       = ''

        try:
            session = Session()
            result = session.query(Booking, UserAddress) \
                            .join(UserAddress, and_(Booking.user_id == UserAddress.user_id, Booking.addr_idx == UserAddress.user_addr_index)) \
                            .filter(Booking.id == booking_id) \
                            .one()

            house_type = result.UserAddress.kind
            size       = result.UserAddress.size

        except NoResultFound, e:
            print_err_detail(e)

        except MultipleResultsFound, e:
            print_err_detail(e)

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()

        return house_type, size

    def get_users_who_register_only(self, start_date):
        session = Session()
        try:
            params  = {}
            params['start_date'] = start_date

            query  = '''select u.id, aes_decrypt(from_base64(name), substr(salt, 1, 16)) as name,
            u.devicetype,
        	aes_decrypt(from_base64(phone), substr(salt, 1, 16)) as phone, dateofreg,
            w.sigungu_id
        	from users u
            left join waiting_users w
            on u.id = w.user_id
            left join user_addresses a
            on u.id = a.user_id
            where date(u.dateofreg) >= :start_date
            and sigungu_id is null
            and address is null
            order by dateofreg
            '''

            result = session.execute(query, params).fetchall()

            users = []
            for row in result:
                user = dict(row)
                user['dateofreg'] = user['dateofreg'].strftime('%Y-%m-%d %H:%M')
                users.append(user)
            return users

        except Exception, e:
            print_err_detail(e)

        finally:
            session.close()


    def get_users_who_add_address_only(self, start_date):
        session = Session()
        try:
            params  = {}
            params['start_date'] = start_date

            query  = '''select id, aes_decrypt(from_base64(name), substr(salt, 1, 16)) as name,
            devicetype,
            aes_decrypt(from_base64(phone), substr(salt, 1, 16)) as phone  ,
            aes_decrypt(from_base64(address), substr(salt, 1, 16)) as address  ,
            dateofreg
            from (
            select u.id, u.devicetype, name, phone, salt, address, request_id, dateofreg
            	from users u
                join user_addresses a
                on u.id = a.user_id
                join user_default_addresses da
                on a.user_id = da.user_id and da.address_idx = 0
                left join bookings b
                on b.user_id = u.id
                where date(u.dateofreg) >= :start_date)t
                where t.request_id is NULL
                order by dateofreg
            '''
            result = session.execute(query, params).fetchall()

            users = []
            for row in result:
                user = dict(row)
                user['dateofreg'] = user['dateofreg'].strftime('%Y-%m-%d %H:%M')
                users.append(user)
            return users
        except Exception, e:
            print_err_detail(e)
        finally:
            session.close()


if __name__ == '__main__':
    start_date = dt.datetime.now() - dt.timedelta(days = 7)

    userdao = UserDAO()
    print userdao.get_users_who_register_only(start_date)
    print userdao.get_users_who_add_address_only(start_date)

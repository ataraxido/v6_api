from c2corg_api.models.document import DocumentLocale
from c2corg_api.models.user_profile import UserProfile
from c2corg_api.views.document import DocumentRest
from functools import partial
from pyramid.httpexceptions import HTTPInternalServerError

from cornice.resource import resource

from c2corg_api.models.user import User, schema_user, schema_create_user
from c2corg_api.views import (
        cors_policy, json_view, restricted_view, restricted_json_view,
        to_json_dict)
from c2corg_api.views.validation import validate_id

from c2corg_api.models import DBSession

from c2corg_api.security.roles import (
    try_login, log_validated_user_i_know_what_i_do,
    remove_token, extract_token, renew_token)

from c2corg_api.security.discourse_client import (
    discourse_sync_sso, discourse_logout)

from c2corg_api.security.discourse_sso_provider import (
    discourse_redirect, discourse_redirect_without_nonce)

from c2corg_api.emails.email_service import get_email_service

from sqlalchemy.sql.expression import and_

import colander
import datetime

import logging
log = logging.getLogger(__name__)

ENCODING = 'UTF-8'
VALIDATION_EXPIRE_DAYS = 3


def validate_json_password(request):
    """Checks if the password was given and encodes it.
       This is done here as the password is not an SQLAlchemy field.
       In addition, we can ensure the password is not leaked in the
       validation error messages.
    """

    if 'password' not in request.json:
        request.errors.add('body', 'password', 'Required')

    try:
        # We receive a unicode string. The hashing function used
        # later on requires plain string otherwise it raises
        # the "Unicode-objects must be encoded before hashing" error.
        password = request.json['password']
        request.validated['password'] = password.encode(ENCODING)
    except:
        request.errors.add('body', 'password', 'Invalid')


def validate_unique_attribute(attrname, request):
    """Checks if the given attribute is unique.
    """

    if attrname in request.json:
        value = request.json[attrname]
        attr = getattr(User, attrname)
        count = DBSession.query(User).filter(attr == value).count()
        if count == 0:
            request.validated[attrname] = value
        else:
            request.errors.add('body', attrname, 'already used ' + attrname)


@resource(path='/users/{id}', cors_policy=cors_policy)
class UserRest(object):
    def __init__(self, request):
        self.request = request

    @restricted_view(validators=validate_id)
    def get(self):
        id = self.request.validated['id']
        user = DBSession. \
            query(User). \
            filter(User.id == id). \
            first()

        return to_json_dict(user, schema_user)


@resource(path='/users/register', cors_policy=cors_policy)
class UserRegistrationRest(object):
    def __init__(self, request):
        self.request = request

    @json_view(schema=schema_create_user, validators=[
        validate_json_password,
        partial(validate_unique_attribute, "email"),
        partial(validate_unique_attribute, "username")])
    def post(self):
        user = schema_create_user.objectify(self.request.validated)
        user.password = self.request.validated['password']
        user.update_validation_nonce(VALIDATION_EXPIRE_DAYS)

        # directly create the user profile, the document id of the profile
        # is the user id
        # TODO to create the profile we need at least one locale. once we have
        # an interface language (https://github.com/c2corg/v6_api/issues/116)
        # we can create the profile in that language.
        lang = 'fr'
        user.profile = UserProfile(
            categories=['amateur'],
            locales=[DocumentLocale(lang=lang, title='')]
        )

        DBSession.add(user)
        try:
            DBSession.flush()
        except:
            log.warning('Error persisting user', exc_info=True)
            raise HTTPInternalServerError('Error persisting user')

        # also create a version for the profile
        DocumentRest.create_new_version(user.profile, user.id)

        # The user needs validation
        email_service = get_email_service(self.request)
        nonce = user.validation_nonce
        settings = self.request.registry.settings
        link = settings['mail.validate_register_url_template'] % nonce
        email_service.send_registration_confirmation(lang, user, link)

        return to_json_dict(user, schema_user)


def validate_user_from_nonce(request):
    nonce = request.matchdict['nonce']
    if nonce is None:
        request.errors.add('querystring', 'nonce', 'missing nonce')
    else:
        now = datetime.datetime.utcnow()
        user = DBSession.query(User).filter(
                and_(
                    User.validation_nonce == nonce,
                    User.validation_nonce_expire > now)).first()
        if user is None:
            request.errors.add('querystring', 'nonce', 'invalid nonce')
        else:
            request.validated['user'] = user


def validate_password(request):
    password = request.matchdict['password']
    if password is None:
        request.errors.add('querystring', 'password', 'missing password')
    else:
        request.validated['password'] = password


@resource(
        path='/users/validate_new_password/{nonce}/{password}',
        cors_policy=cors_policy)
class UserValidateNewPasswordRest(object):
    def __init__(self, request):
        self.request = request

    @json_view(validators=[validate_user_from_nonce, validate_password])
    def post(self):
        request = self.request
        user = request.validated['user']
        user.clear_validation_nonce()
        password = request.validated['password']
        user.password = password

        # The user was validated by the nonce so we can log in
        token = log_validated_user_i_know_what_i_do(user, request)
        try:
            DBSession.flush()
        except:
            log.warning('Error persisting user', exc_info=True)
            raise HTTPInternalServerError('Error persisting user')

        if token:
            settings = request.registry.settings
            response = token_to_response(user, token, request)
            try:
                r = discourse_redirect_without_nonce(user, settings)
                response['redirect_internal'] = r
            except:
                # Any error with discourse should not prevent login
                log.warning(
                    'Error logging into discourse for %d', user.id,
                    exc_info=True)
            return response
        else:
            request.errors.status = 403
            request.errors.add('body', 'user', 'Login failed')
            return None


@resource(
        path='/users/validate_register_email/{nonce}',
        cors_policy=cors_policy)
class UserNonceValidationRest(object):
    def __init__(self, request):
        self.request = request

    def complete_registration(self, user):
        return discourse_sync_sso(user, self.request.registry.settings)

    @json_view(validators=[validate_user_from_nonce])
    def post(self):
        request = self.request
        user = request.validated['user']
        user.clear_validation_nonce()
        user.email_validated = True

        # The user was validated by the nonce so we can log in
        token = log_validated_user_i_know_what_i_do(user, request)
        try:
            DBSession.flush()
        except:
            log.warning('Error persisting user', exc_info=True)
            raise HTTPInternalServerError('Error persisting user')

        if token:
            response = token_to_response(user, token, request)
            settings = request.registry.settings
            try:
                r = discourse_redirect_without_nonce(
                    user, settings)
                response['redirect_internal'] = r
            except:
                # Any error with discourse should not prevent login
                log.warning(
                    'Error logging into discourse for %d', user.id,
                    exc_info=True)
            return response
        else:
            request.errors.status = 403
            request.errors.add('body', 'user', 'Login failed')
            return None


class LoginSchema(colander.MappingSchema):
    username = colander.SchemaNode(colander.String())
    password = colander.SchemaNode(colander.String())

login_schema = LoginSchema()


def token_to_response(user, token, request):
    assert token is not None
    expire_time = token.expire - datetime.datetime(1970, 1, 1)
    roles = ['moderator'] if user.moderator else []
    return {
        'token': token.value,
        'username': user.username,
        'expire': int(expire_time.total_seconds()),
        'roles': roles
    }


@resource(path='/users/login', cors_policy=cors_policy)
class UserLoginRest(object):
    def __init__(self, request):
        self.request = request

    @json_view(schema=login_schema, validators=[validate_json_password])
    def post(self):
        request = self.request
        username = request.validated['username']
        password = request.validated['password']
        user = DBSession.query(User). \
            filter(User.username == username).first()

        token = try_login(user, password, request) if user else None
        if token:
            response = token_to_response(user, token, request)
            if 'discourse' in request.json:
                settings = request.registry.settings
                if 'sso' in request.json and 'sig' in request.json:
                    sso = request.json['sso']
                    sig = request.json['sig']
                    redirect = discourse_redirect(user, sso, sig, settings)
                    response['redirect'] = redirect
                else:
                    try:
                        r = discourse_redirect_without_nonce(
                            user, settings)
                        response['redirect_internal'] = r
                    except:
                        # Any error with discourse should not prevent login
                        log.warning(
                            'Error logging into discourse for %d', user.id,
                            exc_info=True)
            return response
        else:
            request.errors.status = 403
            request.errors.add('body', 'user', 'Login failed')
            return None


@resource(path='/users/renew', cors_policy=cors_policy)
class UserRenewRest(object):
    def __init__(self, request):
        self.request = request

    @restricted_view(renderer='json')
    def post(self):
        request = self.request
        userid = request.authenticated_userid
        user = DBSession.query(User).filter(User.id == userid).first()
        token = renew_token(user, request)
        if token:
            return token_to_response(user, token, request)
        else:
            raise HTTPInternalServerError('Error renewing token')


@resource(path='/users/logout', cors_policy=cors_policy)
class UserLogoutRest(object):
    def __init__(self, request):
        self.request = request

    @restricted_json_view(renderer='json')
    def post(self):
        request = self.request
        userid = request.authenticated_userid
        result = {'user': userid}
        remove_token(extract_token(request))
        if 'discourse' in request.json:
            try:
                settings = request.registry.settings
                result['discourse_user'] = discourse_logout(userid, settings)
            except:
                # Any error with discourse should not prevent logout
                log.warning(
                    'Error logging out of discourse for %d', userid,
                    exc_info=True)
        return result

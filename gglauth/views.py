from django.shortcuts import render
from googleads import oauth2
from oauth2client import client
from googleads import adwords
from django.http import HttpResponse
from urllib.error import HTTPError
from xml.etree import ElementTree
from collections import defaultdict, namedtuple
import json

devToken = "RAPXaNRd9Qsg08dOizs9NA"
clientId = "1028480687198-fsgb8aarmiondq5enmgilnc5lhc8p5eh.apps.googleusercontent.com"
clientsecret = "oLDueu1dfhFknqr3jOodxFK9"
REDIRECT_URL = "http://localhost:8000/redirect"

flow = client.OAuth2WebServerFlow(
    client_id=clientId,
    client_secret=clientsecret,
    scope=oauth2.GetAPIScope('adwords'),
    user_agent='Test',
    approval_prompt='force',
    redirect_uri=REDIRECT_URL,
)

auth_uri = flow.step1_get_authorize_url()

print (auth_uri)


def get_adwords_client(refresh_token, client_customer_id=None):
    client_id = clientId
    client_secret = clientsecret
    oauth2_client = oauth2.GoogleRefreshTokenClient(client_id, client_secret, refresh_token)
    return adwords.AdWordsClient(
        devToken,
        oauth2_client,
        client_customer_id=client_customer_id
    )

def _get_error_from_xml(xml, version):
    namespace = {
        'envelope': 'http://schemas.xmlsoap.org/soap/envelope/',
        'mcm': 'https://adwords.google.com/api/adwords/mcm/{version}'.format(version=version),
        'cm': 'https://adwords.google.com/api/adwords/cm/{version}'.format(version=version),
    }

    # Descend through the XML.
    body = xml.find('envelope:Body', namespace)
    fault = body.find('envelope:Fault', namespace)
    detail = fault.find('detail')
    api_exception_fault = detail.find('mcm:ApiExceptionFault', namespace)
    errors = api_exception_fault.find('cm:errors', namespace)

    # Get the elements we actually want.
    api_error_type = errors.find('cm:ApiError.Type', namespace)
    reason = errors.find('cm:reason', namespace)

    error = namedtuple('error', ('api_error_type', 'reason'))
    return error(api_error_type.text, reason.text)

def get_customers(refresh_token):
    # Will be called outside of a view with no reasonable access to
    # a `User` instance.  Provide a `refresh_token` manually.
    client = get_adwords_client(refresh_token)
    customer_service = client.GetService('CustomerService')
    try:
        customers = customer_service.getCustomers()
    except HTTPError as e:
        if not hasattr(e, 'fp'):
            raise

        data = e.fp.read()
        xml = ElementTree.fromstring(data)
        error = _get_error_from_xml(xml, cls.adwords_api_version)
        if error.api_error_type == 'AuthenticationError' and error.reason == 'NOT_ADS_USER':
            raise

    try:
        managed_customers = []
        for customer in customers:
            customer_id = customer.customerId

            # Get a new client with all the data we need.
            client = get_adwords_client(refresh_token, customer_id)
            managed_customer_service = client.GetService('ManagedCustomerService')
            selector = {
                'fields': [
                    'CustomerId',
                    'Name',
                    'CanManageClients',
                ],
                # No pagination; we will always want all customers.
            }
            try:
                managed_customers.extend(managed_customer_service.get(selector).entries)
            except:
                pass
    except:
        raise

    return managed_customers


def redir(request):
    auth_code = request.GET.get('code', None)
    credentials = flow.step2_exchange(auth_code)
    refresh_token = credentials.refresh_token
    print(auth_code)
    print(credentials)
    print(refresh_token)
    customers = get_customers(refresh_token=refresh_token)
    for customer in customers:
        print(customer)

    return HttpResponse(customers)

import settings
import simplejson
from google.appengine.api.urlfetch import fetch

def get_paypal_headers():
    """
    Utililty method with all required headers for the PayPal request
    """
    return {
        "X-PAYPAL-SECURITY-USERID":     settings.PAYPAL_USER_ID,
        "X-PAYPAL-SECURITY-PASSWORD":    settings.PAYPAL_PASSWORD,
        "X-PAYPAL-SECURITY-SIGNATURE":   settings.PAYPAL_SIGNATURE,
        "X-PAYPAL-APPLICATION-ID":       settings.PAYPAL_APPLICATION_ID,
        "X-PAYPAL-REQUEST-DATA-FORMAT":  settings.PAYPAL_REQUEST_DATA_FORMAT,
        "X-PAYPAL-RESPONSE-DATA-FORMAT": settings.PAYPAL_RESPONSE_DATA_FORMAT,
        "Content-Type":                  "application/json"
    }


def create_pay_request(donation_amount, charities):
    """
    Utility method to build a the PayPal Pay request for starting 
    the transaction process. The response will contain a payKey that
    will be used when we redirect the user to PayPal to complete the
    transaction.
    """

    # Try to split the donation amount equally amount all charities
    l = len(charities)
    split_amount = round(donation_amount/l, 2)

    # Test that the amount was equally split. If it's not we must
    # adjust one of the split amounts to make the sum of the donation
    # be what the user wants
    n = split_amount * l

    # Equal split
    if n == donation_amount:
        fraction = 0.00
    # Sum is greater than the user's donation amount so adjust the
    # amount by -0.01
    elif n > donation_amount:
        fraction = -0.01
    # Sum is less than the user's donation amount so adjust the
    # amount by +0.01
    else:
        fraction = 0.01

    # Build the list of receivers. Each receiver will be the charity
    # and the amount will be the split amount. The first charity will
    # get the fractional amount added or substracted.
    receiver_list = []
    sum = 0
    for i in range(len(charities)):
        r = {
            "email": charities[i].email,
        }
        
        # Add the fraction to the first charity's amount
        amount = split_amount
        if i == 0:
            amount += fraction
        sum += amount

        # convert the amount to a string with precision of 2 and add
        # the receiver to the list
        r['amount'] = "%0.2f" % amount
        receiver_list.append(r)

    # Build the JSON object for the payment request. All of this is pretty
    # standard stuff and can be found in the Adaptive Payments documentation
    json = {
        "returnUrl": settings.RETURN_URL,
        "cancelUrl": settings.CANCEL_URL,
        "receiverList": {
            "receiver": receiver_list
        },
        "currencyCode": "USD",
        "actionType": "PAY",
        "reverseAllParallelPaymentsOnError": True,
        "requestEnvelope": {"errorLanguage": "en_US"}
    }

    # Use Google's fetch method to send the pay request to PayPal. The response
    # will contain the payKey.
    response = fetch(settings.API_ENDPOINT+"/Pay",
        payload=simplejson.dumps(json),
        method="POST",
        headers=get_paypal_headers())

    return simplejson.loads(response.content)

def get_pay_key(response):
    """
    Utility method to retrieve the payKey from a PayPal response
    """
    return response.get("payKey")

def get_errors(response):
    """
    Utility method to retrieve the list of errors (if any) from a 
    PayPal response.
    """
    errors = response.get("error")
    if errors:
        return [e.get("message") for e in errors]
    return None

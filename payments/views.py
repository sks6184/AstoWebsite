from django.http import HttpResponse
from django.views.decorators.http import require_POST


@require_POST
def webhook_placeholder(request):
    """S-8: fail closed until a signed payment webhook is implemented.

    GET and other methods receive 405. POST is never treated as a successful
    payment event: it receives 501 and changes no state.
    """
    return HttpResponse("Payment webhook is not implemented.", status=501, content_type="text/plain")

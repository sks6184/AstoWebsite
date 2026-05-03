from django.http import HttpResponse


def webhook_placeholder(request):
    return HttpResponse("Payment webhook endpoint ready.")

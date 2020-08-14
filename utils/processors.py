"""Define global attributes for templates"""
def extend(request):
    return {'url_name': request.resolver_match.url_name}

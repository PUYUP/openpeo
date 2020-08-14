def PersonRequestMiddleware(get_response):
    """ Append person to all request """
    def middleware(request):
        person = getattr(request.user, 'person', None)
        person_pk = getattr(person, 'id', None)
        person_uuid = getattr(person, 'uuid', None)

        setattr(request, 'person', person)
        setattr(request, 'person_pk', person_pk)
        setattr(request, 'person_uuid', person_uuid)

        response = get_response(request)
        return response
    return middleware

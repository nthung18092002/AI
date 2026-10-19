"""Local AI connections bypass proxies and reject redirects to remote services."""
import urllib.parse
import urllib.request


def local_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password:
        raise ValueError('AI chỉ được kết nối HTTP local: 127.0.0.1, localhost hoặc ::1.')
    return url


class LocalRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        local_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_local(req, timeout=30):
    local_url(req if isinstance(req, str) else req.full_url)
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), LocalRedirect()).open(req, timeout=timeout)

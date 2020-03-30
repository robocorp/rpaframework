###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Global

.. raw:: html

   <p>RPA Framework HTTP library which wraps <span class="name">RequestsLibrary &lt;https://hub.robocorp.com/libraries/bulkan-robotframework-requests/&gt;</span>_ functionality.</p>

********
Keywords
********

:Create Client Cert Session:
  :Arguments: alias, url, headers={}, cookies={}, client_certs=None, timeout=None, proxies=None, verify=False, debug=0, max_retries=3, backoff_factor=0.1, disable_warnings=0, retry_status_list=[], retry_method_list=['DELETE', 'PUT', 'OPTIONS', 'GET', 'HEAD', 'TRACE']

  .. raw:: html

     <p>Create Session: create a HTTP session to a server</p>
     <p><code>url</code> Base url of the server</p>
     <p><code>alias</code> Robot Framework alias to identify the session</p>
     <p><code>headers</code> Dictionary of default headers</p>
     <p><code>cookies</code> Dictionary of cookies</p>
     <p><code>client_certs</code> ['client certificate', 'client key'] PEM files containing the client key and certificate</p>
     <p><code>timeout</code> Connection timeout</p>
     <p><code>proxies</code> Dictionary that contains proxy urls for HTTP and HTTPS communication</p>
     <p><code>verify</code> Whether the SSL cert will be verified. A CA_BUNDLE path can also be provided. Defaults to False.</p>
     <p><code>debug</code> Enable http verbosity option more information <a href="https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel">https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel</a></p>
     <p><code>max_retries</code> Number of maximum retries each connection should attempt. By default it will retry 3 times in case of connection errors only. A 0 value will disable any kind of retries regardless of other retry settings. In case the number of retries is reached a retry exception is raised.</p>
     <p><code>disable_warnings</code> Disable requests warning useful when you have large number of testcases</p>
     <p><code>backoff_factor</code> Introduces a delay time between retries that is longer after each retry. eg. if backoff_factor is set to 0.1 the sleep between attemps will be: 0.0, 0.2, 0.4 More info here: <a href="https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html">https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html</a></p>
     <p><code>retry_method_list</code> List of uppercased HTTP method verbs where retries are allowed. By default retries are allowed only on HTTP requests methods that are considered to be idempotent (multiple requests with the same parameters end with the same state). eg. set to ['POST', 'GET'] to retry only those kind of requests.</p>
     <p><code>retry_status_list</code> List of integer HTTP status codes that, if returned, a retry is attempted. eg. set to [502, 503] to retry requests if those status are returned. Note that max_retries must be greater than 0.</p>

:Create Custom Session:
  :Arguments: alias, url, auth, headers={}, cookies={}, timeout=None, proxies=None, verify=False, debug=0, max_retries=3, backoff_factor=0.1, disable_warnings=0, retry_status_list=[], retry_method_list=['DELETE', 'PUT', 'OPTIONS', 'GET', 'HEAD', 'TRACE']

  .. raw:: html

     <p>Create Session: create a HTTP session to a server</p>
     <p><code>url</code> Base url of the server</p>
     <p><code>alias</code> Robot Framework alias to identify the session</p>
     <p><code>headers</code> Dictionary of default headers</p>
     <p><code>cookies</code> Dictionary of cookies</p>
     <p><code>auth</code> A Custom Authentication object to be passed on to the requests library. <a href="http://docs.python-requests.org/en/master/user/advanced/#custom-authentication">http://docs.python-requests.org/en/master/user/advanced/#custom-authentication</a></p>
     <p><code>timeout</code> Connection timeout</p>
     <p><code>proxies</code> Dictionary that contains proxy urls for HTTP and HTTPS communication</p>
     <p><code>verify</code> Whether the SSL cert will be verified. A CA_BUNDLE path can also be provided. Defaults to False.</p>
     <p><code>debug</code> Enable http verbosity option more information <a href="https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel">https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel</a></p>
     <p><code>max_retries</code> Number of maximum retries each connection should attempt. By default it will retry 3 times in case of connection errors only. A 0 value will disable any kind of retries regardless of other retry settings. In case the number of retries is reached a retry exception is raised.</p>
     <p><code>disable_warnings</code> Disable requests warning useful when you have large number of testcases</p>
     <p><code>backoff_factor</code> Introduces a delay time between retries that is longer after each retry. eg. if backoff_factor is set to 0.1 the sleep between attemps will be: 0.0, 0.2, 0.4 More info here: <a href="https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html">https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html</a></p>
     <p><code>retry_method_list</code> List of uppercased HTTP method verbs where retries are allowed. By default retries are allowed only on HTTP requests methods that are considered to be idempotent (multiple requests with the same parameters end with the same state). eg. set to ['POST', 'GET'] to retry only those kind of requests.</p>
     <p><code>retry_status_list</code> List of integer HTTP status codes that, if returned, a retry is attempted. eg. set to [502, 503] to retry requests if those status are returned. Note that max_retries must be greater than 0.</p>

:Create Digest Session:
  :Arguments: alias, url, auth, headers={}, cookies={}, timeout=None, proxies=None, verify=False, debug=0, max_retries=3, backoff_factor=0.1, disable_warnings=0, retry_status_list=[], retry_method_list=['DELETE', 'PUT', 'OPTIONS', 'GET', 'HEAD', 'TRACE']

  .. raw:: html

     <p>Create Session: create a HTTP session to a server</p>
     <p><code>url</code> Base url of the server</p>
     <p><code>alias</code> Robot Framework alias to identify the session</p>
     <p><code>headers</code> Dictionary of default headers</p>
     <p><code>cookies</code> Dictionary of cookies</p>
     <p><code>auth</code> ['DOMAIN', 'username', 'password'] for NTLM Authentication</p>
     <p><code>timeout</code> Connection timeout</p>
     <p><code>proxies</code> Dictionary that contains proxy urls for HTTP and HTTPS communication</p>
     <p><code>verify</code> Whether the SSL cert will be verified. A CA_BUNDLE path can also be provided. Defaults to False.</p>
     <p><code>debug</code> Enable http verbosity option more information <a href="https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel">https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel</a></p>
     <p><code>max_retries</code> Number of maximum retries each connection should attempt. By default it will retry 3 times in case of connection errors only. A 0 value will disable any kind of retries regardless of other retry settings. In case the number of retries is reached a retry exception is raised.</p>
     <p><code>disable_warnings</code> Disable requests warning useful when you have large number of testcases</p>
     <p><code>backoff_factor</code> Introduces a delay time between retries that is longer after each retry. eg. if backoff_factor is set to 0.1 the sleep between attemps will be: 0.0, 0.2, 0.4 More info here: <a href="https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html">https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html</a></p>
     <p><code>retry_method_list</code> List of uppercased HTTP method verbs where retries are allowed. By default retries are allowed only on HTTP requests methods that are considered to be idempotent (multiple requests with the same parameters end with the same state). eg. set to ['POST', 'GET'] to retry only those kind of requests.</p>
     <p><code>retry_status_list</code> List of integer HTTP status codes that, if returned, a retry is attempted. eg. set to [502, 503] to retry requests if those status are returned. Note that max_retries must be greater than 0.</p>

:Create Ntlm Session:
  :Arguments: alias, url, auth, headers={}, cookies={}, timeout=None, proxies=None, verify=False, debug=0, max_retries=3, backoff_factor=0.1, disable_warnings=0, retry_status_list=[], retry_method_list=['DELETE', 'PUT', 'OPTIONS', 'GET', 'HEAD', 'TRACE']

  .. raw:: html

     <p>Create Session: create a HTTP session to a server</p>
     <p><code>url</code> Base url of the server</p>
     <p><code>alias</code> Robot Framework alias to identify the session</p>
     <p><code>headers</code> Dictionary of default headers</p>
     <p><code>cookies</code> Dictionary of cookies</p>
     <p><code>auth</code> ['DOMAIN', 'username', 'password'] for NTLM Authentication</p>
     <p><code>timeout</code> Connection timeout</p>
     <p><code>proxies</code> Dictionary that contains proxy urls for HTTP and HTTPS communication</p>
     <p><code>verify</code> Whether the SSL cert will be verified. A CA_BUNDLE path can also be provided. Defaults to False.</p>
     <p><code>debug</code> Enable http verbosity option more information <a href="https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel">https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel</a></p>
     <p><code>max_retries</code> Number of maximum retries each connection should attempt. By default it will retry 3 times in case of connection errors only. A 0 value will disable any kind of retries regardless of other retry settings. In case the number of retries is reached a retry exception is raised.</p>
     <p><code>disable_warnings</code> Disable requests warning useful when you have large number of testcases</p>
     <p><code>backoff_factor</code> Introduces a delay time between retries that is longer after each retry. eg. if backoff_factor is set to 0.1 the sleep between attemps will be: 0.0, 0.2, 0.4 More info here: <a href="https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html">https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html</a></p>
     <p><code>retry_method_list</code> List of uppercased HTTP method verbs where retries are allowed. By default retries are allowed only on HTTP requests methods that are considered to be idempotent (multiple requests with the same parameters end with the same state). eg. set to ['POST', 'GET'] to retry only those kind of requests.</p>
     <p><code>retry_status_list</code> List of integer HTTP status codes that, if returned, a retry is attempted. eg. set to [502, 503] to retry requests if those status are returned. Note that max_retries must be greater than 0.</p>

:Create Session:
  :Arguments: alias, url, headers={}, cookies={}, auth=None, timeout=None, proxies=None, verify=False, debug=0, max_retries=3, backoff_factor=0.1, disable_warnings=0, retry_status_list=[], retry_method_list=['DELETE', 'PUT', 'OPTIONS', 'GET', 'HEAD', 'TRACE']

  .. raw:: html

     <p>Create Session: create a HTTP session to a server</p>
     <p><code>alias</code> Robot Framework alias to identify the session</p>
     <p><code>url</code> Base url of the server</p>
     <p><code>headers</code> Dictionary of default headers</p>
     <p><code>cookies</code> Dictionary of cookies</p>
     <p><code>auth</code> List of username &amp; password for HTTP Basic Auth</p>
     <p><code>timeout</code> Connection timeout</p>
     <p><code>proxies</code> Dictionary that contains proxy urls for HTTP and HTTPS communication</p>
     <p><code>verify</code> Whether the SSL cert will be verified. A CA_BUNDLE path can also be provided.</p>
     <p><code>debug</code> Enable http verbosity option more information <a href="https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel">https://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.set_debuglevel</a></p>
     <p><code>max_retries</code> Number of maximum retries each connection should attempt. By default it will retry 3 times in case of connection errors only. A 0 value will disable any kind of retries regardless of other retry settings. In case the number of retries is reached a retry exception is raised.</p>
     <p><code>disable_warnings</code> Disable requests warning useful when you have large number of testcases</p>
     <p><code>backoff_factor</code> Introduces a delay time between retries that is longer after each retry. eg. if backoff_factor is set to 0.1 the sleep between attemps will be: 0.0, 0.2, 0.4 More info here: <a href="https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html">https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html</a></p>
     <p><code>retry_method_list</code> List of uppercased HTTP method verbs where retries are allowed. By default retries are allowed only on HTTP requests methods that are considered to be idempotent (multiple requests with the same parameters end with the same state). eg. set to ['POST', 'GET'] to retry only those kind of requests.</p>
     <p><code>retry_status_list</code> List of integer HTTP status codes that, if returned, a retry is attempted. eg. set to [502, 503] to retry requests if those status are returned. Note that max_retries must be greater than 0.</p>

:Delete All Sessions:
  .. raw:: html

     <p>Removes all the session objects</p>

:Delete Request:
  :Arguments: alias, uri, data=None, json=None, params=None, headers=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send a DELETE request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the DELETE request to</p>
     <p><code>json</code> a value that will be json encoded and sent as request data if data is not specified</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>timeout</code> connection timeout</p>

:Get Request:
  :Arguments: alias, uri, headers=None, data=None, json=None, params=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send a GET request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the GET request to</p>
     <p><code>params</code> url parameters to append to the uri</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>data</code> a dictionary of key-value pairs that will be urlencoded and sent as GET data or binary data that is sent as the raw body content</p>
     <p><code>json</code> a value that will be json encoded and sent as GET data if data is not specified</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>timeout</code> connection timeout</p>

:Head Request:
  :Arguments: alias, uri, headers=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send a HEAD request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the HEAD request to</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>timeout</code> connection timeout</p>

:Options Request:
  :Arguments: alias, uri, headers=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send an OPTIONS request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the OPTIONS request to</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>timeout</code> connection timeout</p>

:Patch Request:
  :Arguments: alias, uri, data=None, json=None, params=None, headers=None, files=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send a PATCH request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the PATCH request to</p>
     <p><code>data</code> a dictionary of key-value pairs that will be urlencoded and sent as PATCH data or binary data that is sent as the raw body content</p>
     <p><code>json</code> a value that will be json encoded and sent as PATCH data if data is not specified</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>files</code> a dictionary of file names containing file data to PATCH to the server</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>params</code> url parameters to append to the uri</p>
     <p><code>timeout</code> connection timeout</p>

:Post Request:
  :Arguments: alias, uri, data=None, json=None, params=None, headers=None, files=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send a POST request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the POST request to</p>
     <p><code>data</code> a dictionary of key-value pairs that will be urlencoded and sent as POST data or binary data that is sent as the raw body content or passed as such for multipart form data if <code>files</code> is also defined</p>
     <p><code>json</code> a value that will be json encoded and sent as POST data if files or data is not specified</p>
     <p><code>params</code> url parameters to append to the uri</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>files</code> a dictionary of file names containing file data to POST to the server</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>timeout</code> connection timeout</p>

:Put Request:
  :Arguments: alias, uri, data=None, json=None, params=None, files=None, headers=None, allow_redirects=None, timeout=None

  .. raw:: html

     <p>Send a PUT request on the session object found using the given <span class="name">alias</span></p>
     <p><code>alias</code> that will be used to identify the Session object in the cache</p>
     <p><code>uri</code> to send the PUT request to</p>
     <p><code>data</code> a dictionary of key-value pairs that will be urlencoded and sent as PUT data or binary data that is sent as the raw body content</p>
     <p><code>json</code> a value that will be json encoded and sent as PUT data if data is not specified</p>
     <p><code>headers</code> a dictionary of headers to use with the request</p>
     <p><code>allow_redirects</code> Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.</p>
     <p><code>params</code> url parameters to append to the uri</p>
     <p><code>timeout</code> connection timeout</p>

:Request Should Be Successful:
  :Arguments: response

  .. raw:: html

     <p>Fails if response status code is a client or server error (4xx, 5xx).</p>
     <p>The <code>response</code> is the output of other requests keywords like <code>Get Request</code>.</p>
     <p>In case of failure an HTTPError will be automatically raised.</p>

:Session Exists:
  :Arguments: alias

  .. raw:: html

     <p>Return True if the session has been already created</p>
     <p><code>alias</code> that has been used to identify the Session object in the cache</p>

:Status Should Be:
  :Arguments: expected_status, response, msg=None

  .. raw:: html

     <p>Fails if response status code is different than the expected.</p>
     <p><code>expected_status</code> could be the code number as an integer or as string. But it could also be a named status code like 'ok', 'created', 'accepted' or 'bad request', 'not found' etc.</p>
     <p>The <code>response</code> is the output of other requests keywords like <code>Get Request</code>.</p>
     <p>A custom message <code>msg</code> can be added to work like built in keywords.</p>

:To Json:
  :Arguments: content, pretty_print=False

  .. raw:: html

     <p>Convert a string to a JSON object</p>
     <p><code>content</code> String content to convert into JSON</p>
     <p><code>pretty_print</code> If defined, will output JSON is pretty print format</p>

:Update Session:
  :Arguments: alias, headers=None, cookies=None

  .. raw:: html

     <p>Update Session Headers: update a HTTP Session Headers</p>
     <p><code>alias</code> Robot Framework alias to identify the session</p>
     <p><code>headers</code> Dictionary of headers merge into session</p>

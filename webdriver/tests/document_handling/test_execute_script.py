import pytest

from tests.support.asserts import assert_same_element
from tests.support.asserts import assert_success, assert_error
from tests.support.fixtures import create_dialog

from tests.support.inline import inline
from webdriver.client import element_key


# Ported from Mozilla's marionette's test suite.

# TODO:
# * Return a window proxy
# * Throw an exception during JS execution
# * All error cases
# * Probably more.


def assert_elements_equal(session, expected, actual):
    assert len(expected) == len(actual)
    for e, a in zip(expected, actual):
        e_id = e if isinstance(e, dict) else e.json()
        a_id = a if isinstance(a, dict) else a.json()
        assert_same_element(session, e_id, a_id)


def find_css(session, selector):
    return session.send_session_command("POST", "element",
                                        {"using": "css selector",
                                         "value": selector})


def find_css_all(session, selector):
    return session.send_session_command("POST", "elements",
                                        {"using": "css selector",
                                         "value": selector})


def generate_async_script(script):
    modified_script = script.replace("arguments[", "actualArgs[")
    async_script = """
        let nrActualArgs = arguments.length - 1;
        let callback = arguments[nrActualArgs];
        let actualArgs = []; 
        for(let i = 0; i < nrActualArgs; ++i) {
            actualArgs.push(arguments[i]); 
        }
        callback(function() { %s;}());"""
    return async_script % modified_script


def execute_script(session, script, args=None):
    if args is None:
        args = []
    return execute_common(args, script, "sync", session)


def execute_async_script(session, script, args=None):
    if args is None:
        args = []
    return execute_common(args, generate_async_script(script), "async", session)


def execute_common(args, script, exec_method, session):
    return session.transport.send("POST", "session/{0}/execute/{1}".format(session.session_id, exec_method), {
        'script': script,
        'args': list(args)})


executors = [
    execute_script,
    execute_async_script
]


# 15.2 extract the script arguments from a request

@pytest.mark.parametrize("exec_method", ["sync", "async"])
def test_request_argument_parsing(session, exec_method, create_window):
    # step 2
    session.url = inline("""<title>JS testing</title>""")
    result = session.transport.send("POST", "session/{0}/execute/{1}".format(session.session_id, exec_method), {
         'script': 1,
         'args': [2,3]})

    assert_error(result, "invalid argument")

    # step 5
    result = session.transport.send("POST", "session/{0}/execute/{1}".format(session.session_id, exec_method), {
         'script': "",
         'args': "no array"})

    assert_error(result, "invalid argument")

    session.window_handle = create_window()
    session.close()
    # step 1
    assert_error(execute_script(session, "return 1"), "no such window")

# 15.2.1/2 Execute Script (Async)
@pytest.mark.parametrize("executor", executors)
def test_no_browsing_context(session, executor, create_window):
    session.window_handle = create_window()
    session.close()
    # step 2
    assert_error(executor(session, "return 1"), "no such window")


prompts_types = ["alert", "confirm", "prompt"]


def user_prompts_params(handler_list):
    return map(lambda p: (execute_script, p), handler_list) + \
           map(lambda p: (execute_async_script, p), handler_list)


def unexpected_alert_with_prompt_type(session, executor, prompt_type):
    create_dialog(session)(prompt_type, text=prompt_type + " #1", result_var=prompt_type + "1")
    result = executor(session, "return 1")
    assert_error(result, "unexpected alert open")
    session.alert.dismiss()


user_prompt_handlers_error = ["dismiss and notify", "accept and notify", "ignore"]


# 15.2.1/2 Execute Script (Async)
@pytest.mark.parametrize("executor, handler_type", user_prompts_params(user_prompt_handlers_error))
def test_user_prompts_errors(new_session, executor, handler_type):
    _, session = new_session({"alwaysMatch": {"unhandledPromptBehavior": handler_type}})
    session.url = inline("""<title>JS testing</title>""")
    # step 3

    for prompt_type in prompts_types:
        unexpected_alert_with_prompt_type(session, executor, prompt_type)


user_prompt_handlers_pass = ["dismiss", "accept"]


# 15.2.1/2 Execute Script (Async)
def expected_alert_with_prompt_type(session, executor, prompt_type):
    create_dialog(session)(prompt_type, text=prompt_type + " #1", result_var=prompt_type + "1")
    assert_success(executor(session, "return 1"), 1)
    session.alert.dismiss()


@pytest.mark.parametrize("executor, handler_type", user_prompts_params(user_prompt_handlers_pass))
def test_user_prompts_success(new_session, executor, handler_type):
    _, session = new_session({"alwaysMatch": {"unhandledPromptBehavior": handler_type}})
    session.url = inline("""<title>JS testing</title>""")
    # step 3

    for prompt_type in prompts_types:
        expected_alert_with_prompt_type(session, executor, prompt_type)


@pytest.mark.parametrize("executor", executors)
def test_return_number(session, executor):
    session.url = inline("""<title>JS testing</title>""")

    assert_success(executor(session, "return 1"), 1)
    assert_success(executor(session, "return 1.5"), 1.5)


@pytest.mark.parametrize("executor", executors)
def test_return_boolean(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return true"), True)


@pytest.mark.parametrize("executor", executors)
def test_return_string(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return 'foo'"), "foo")


@pytest.mark.parametrize("executor", executors)
def test_return_array(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return [1, 2]"), [1, 2])
    assert_success(executor(session, "return [true, false]"), [True, False])
    assert_success(executor(session, "return ['foo', 'bar']"), ["foo", "bar"])
    assert_success(executor(session, "return [1, [2]]"), [1, [2]])
    assert_success(executor(session, "return [1, 1.5, true, 'foo']"), [1, 1.5, True, "foo"])
    assert_success(executor(session, "return [1.25, 1.75]"), [1.25, 1.75])


@pytest.mark.parametrize("executor", executors)
def test_return_object(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return {foo: 1}"), {"foo": 1})
    assert_success(executor(session, "return {foo: 1.5}"), {"foo": 1.5})
    assert_success(executor(session, "return {foo: true}"), {"foo": True})
    assert_success(executor(session, "return {foo: 'bar'}"), {"foo": "bar"})
    assert_success(executor(session, "return {foo: [1, 2]}"), {"foo": [1, 2]})
    assert_success(executor(session, "return {foo: {bar: [1, 2]}}"), {"foo": {"bar": [1, 2]}})


@pytest.mark.parametrize("executor", executors)
def test_no_return_value(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "true"), None)


@pytest.mark.parametrize("executor", executors)
def test_argument_null(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=(None,)), None)


@pytest.mark.parametrize("executor", executors)
def test_argument_number(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=(1,)), 1)
    assert_success(executor(session, "return arguments[0]", args=(1.5,)), 1.5)


@pytest.mark.parametrize("executor", executors)
def test_argument_boolean(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=(True,)), True)


@pytest.mark.parametrize("executor", executors)
def test_argument_string(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=("foo",)), "foo")


@pytest.mark.parametrize("executor", executors)
def test_argument_array(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=([1, 2],)), [1, 2])


@pytest.mark.parametrize("executor", executors)
def test_argument_object(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session,
                            "return arguments[0]", args=({"foo": 1},)), {"foo": 1})


ps = ["document", "navigator", "window"]


def generate_parameters():
    return map(lambda p: (execute_script, p), ps) + \
           map(lambda p: (execute_async_script, p), ps)


@pytest.mark.parametrize("executor,p", generate_parameters())
def test_access_to_default_globals(session, executor, p):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session,
                            "return typeof arguments[0] != 'undefined' ? arguments[0] : null",
                            args=(p,)), p)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element(session, executor):
    session.url = inline("""<p>Cheese""")
    expected = find_css(session, "p")
    actual = assert_success(executor(session,
                                     "return document.querySelector('p')"))
    assert_same_element(session, actual, expected)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element_array(session, executor):
    session.url = inline("""<p>Cheese <p>Peas""")
    expected = find_css_all(session, "p")
    actual = assert_success(executor(session, """
            let els = document.querySelectorAll('p');
            return [els[0], els[1]]"""))
    assert_elements_equal(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element_nodelist(session, executor):
    session.url = inline("""<p>Peas <p>Cheese""")
    expected = find_css_all(session, "p")
    actual = assert_success(executor(session, "return document.querySelectorAll('p')"))
    assert_elements_equal(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_sandbox_reuse(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    executor(session, "window.foobar = [23, 42];")
    assert_success(executor(session, "return window.foobar"), [23, 42])


@pytest.mark.parametrize("executor", executors)
def test_no_args(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session,
                            "return typeof arguments[0] == 'undefined'"))


@pytest.mark.parametrize("executor", executors)
def test_to_json(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, """
            return {
              toJSON () {
                return "foo";
              }
            }"""), "foo")


@pytest.mark.parametrize("executor", executors)
def test_unsafe_to_json(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    actual = assert_success(executor(session, """
            return {
              toJSON () {
                return document.documentElement;
              }
            }"""))
    expected = assert_success(executor(session, "return document.documentElement"))
    assert_same_element(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_html_all_collection(session, executor):
    session.url = inline("<p>foo <p>bar")
    els = assert_success(executor(session, "return document.all"))

    # <html>, <head>, <body>, <p>, <p>
    assert 5 == len(els)


@pytest.mark.parametrize("executor", executors)
def test_html_form_controls_collection(session, executor):
    session.url = inline("<form><input><input></form>")
    actual = assert_success(executor(session, "return document.forms[0].elements"))
    expected = find_css_all(session, "input")
    assert_elements_equal(session, expected, actual)

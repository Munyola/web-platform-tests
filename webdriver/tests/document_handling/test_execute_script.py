import pytest

from tests.support.asserts import assert_same_element
from tests.support.asserts import assert_success

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
        e_id = e[element_key] if isinstance(e, dict) else e.json()[element_key]
        a_id = a[element_key] if isinstance(a, dict) else a.json()[element_key]
        assert e_id == a_id


# All tests navigate to an HTML page to ensure that JS
# can be executed. It's unknown whether the default start
# page for all browsers allows JS execution.

def generateAsyncScript(script):
    return """
        var nrActualArgs = arguments.length - 1;
        var callback = arguments[nrActualArgs];
        var actualArgs = []; 
        for(var i = 0; i < nrActualArgs; ++i) {
            actualArgs.push(arguments[i]); 
        }
        callback(function() { """ + script.replace("arguments[", "actualArgs[") + ";}());"


def execute_script(session, script, args = []):
    return execute_common(args, script, "sync", session)

def execute_async_script(session, script, args = []):
    return execute_common(args, generateAsyncScript(script), "async", session)

def execute_common(args, async_script, commandId, session):
    return session.transport.send("POST", "session/%s/execute/%s" % commandId % session.session_id, {
        'script': async_script,
        'args': list(args)})


executors = [
    execute_script,
    execute_async_script
]

@pytest.mark.parametrize("executor", executors)
def test_return_number(session, executor):
    session.url = inline("""<title>JS testing</title>""")

    assert_success(executor(session,"return 1"), 1)
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
    assert_success(executor(session, "return ['foo', 'bar']"), ["foo", "bar"] )
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
    assert_success(executor(session, "return {foo: {bar: [1, 2]}}"), {"foo": {"bar": [1, 2]}} )

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
    assert_success(executor(session, "return arguments[0]", args=(True, )), True)

@pytest.mark.parametrize("executor", executors)
def test_argument_string(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=("foo",)), "foo")

@pytest.mark.parametrize("executor", executors)
def test_argument_array(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, "return arguments[0]", args=([1, 2],)), [1, 2] )


@pytest.mark.parametrize("executor", executors)
def test_argument_object(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session,
            "return arguments[0]", args=({"foo": 1},)), {"foo": 1})

ps = ["document", "navigator", "window"]

def generateParams():
    ret = map(lambda p: (execute_script, p), ps)
    return ret + map(lambda p: (execute_async_script, p), ps)

@pytest.mark.parametrize("executor,p", generateParams())
def test_access_todefault_globals(session, executor, p):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session,
        "return typeof arguments[0] != 'undefined' ? arguments[0] : null",
        args=(p,)), p)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element(session, executor):
    session.url = inline("""<p>Cheese""")
    expected = session.find.css("p", all=False)
    actual = assert_success(executor(session,
            "return document.querySelector('p')"))
    assert_same_element(session, expected.json(), actual)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element_array(session, executor):
    session.url = inline("""<p>Cheese <p>Peas""")
    expected = session.find.css("p")
    actual = assert_success(executor(session, """
            let els = document.querySelectorAll('p');
            return [els[0], els[1]]"""))
    assert_elements_equal(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element_nodelist(session, executor):
    session.url = inline("""<p>Peas <p>Cheese""")
    expected = session.find.css("p")
    actual = assert_success(executor(session, "return document.querySelectorAll('p')"))
    assert_elements_equal(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_sandbox_reuse(session, executor):
    session.url= inline("""<title>JS testing</title>""")
    executor(session, "window.foobar = [23, 42];")
    assert_success(executor(session, "return window.foobar"), [23, 42])


@pytest.mark.parametrize("executor", executors)
def test_no_args(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session,
        "return typeof arguments[0] == 'undefined'"))


@pytest.mark.parametrize("executor", executors)
def test_toJSON(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert_success(executor(session, """
            return {
              toJSON () {
                return "foo";
              }
            }"""), "foo")


@pytest.mark.parametrize("executor", executors)
def test_unsafe_toJSON(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    el = assert_success(executor(session, """
            return {
              toJSON () {
                return document.documentElement;
              }
            }"""))
    expected = assert_success(executor(session, "return document.documentElement"))
    assert_same_element(session, expected, el)


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
    expected = session.find.css("input")
    assert_elements_equal(session, expected, actual)

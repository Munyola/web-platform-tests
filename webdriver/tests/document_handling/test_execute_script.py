import pytest

from tests.support.asserts import assert_same_element
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

def asyncExecute (session, script, args = []):
    newScript = script.replace("arguments[", "actualArgs[")
    val = session.execute_async_script("""
        var nrActualArgs = arguments.length - 1;
        var callback = arguments[nrActualArgs];
        var actualArgs = []; 
        for(var i = 0; i < nrActualArgs; ++i) {
            actualArgs.push(arguments[i]); 
        }
        callback(function() { """ + newScript + ";}());", args)
    return val

def syncExecute (session, script, args = []):
    return session.execute_script(script, args)

executors = [
    syncExecute,
    asyncExecute
]


@pytest.mark.parametrize("executor", executors)
def test_return_number(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert 1 == executor(session,"return 1")
    assert 1.5 == executor(session, "return 1.5")

@pytest.mark.parametrize("executor", executors)
def test_return_boolean(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert True == executor(session, "return true")

@pytest.mark.parametrize("executor", executors)
def test_return_string(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert "foo" == executor(session, "return 'foo'")

@pytest.mark.parametrize("executor", executors)
def test_return_array(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert [1, 2] ==  executor(session, "return [1, 2]")
    assert [1.25, 1.75] ==  executor(session, "return [1.25, 1.75]")
    assert [True, False] == executor(session, "return [true, false]")
    assert ["foo", "bar"] == executor(session, "return ['foo', 'bar']")
    assert [1, 1.5, True, "foo"] == executor(session, "return [1, 1.5, true, 'foo']")
    assert [1, [2]] == executor(session, "return [1, [2]]")

@pytest.mark.parametrize("executor", executors)
def test_return_object(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert {"foo": 1} == executor(session, "return {foo: 1}")
    assert {"foo": 1.5} == executor(session, "return {foo: 1.5}")
    assert {"foo": True} == executor(session, "return {foo: true}")
    assert {"foo": "bar"} == executor(session, "return {foo: 'bar'}")
    assert {"foo": [1, 2]} == executor(session, "return {foo: [1, 2]}")
    assert {"foo": {"bar": [1, 2]}} == \
        executor(session, "return {foo: {bar: [1, 2]}}")

@pytest.mark.parametrize("executor", executors)
def test_no_return_value(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert None == executor(session, "true")

@pytest.mark.parametrize("executor", executors)
def test_argument_null(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert None == executor(session, "return arguments[0]", args=[None])

@pytest.mark.parametrize("executor", executors)
def test_argument_number(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert 1 == executor(session, "return arguments[0]", args=[1])
    assert 1.5 == executor(session, "return arguments[0]", args=[1.5])

@pytest.mark.parametrize("executor", executors)
def test_argument_boolean(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert True == executor(session, "return arguments[0]", args=[True])

@pytest.mark.parametrize("executor", executors)
def test_argument_string(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert "foo" == executor(session, "return arguments[0]", args=["foo"])

@pytest.mark.parametrize("executor", executors)
def test_argument_array(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert [1, 2] == executor(session, "return arguments[0]", args=[[1, 2]])


@pytest.mark.parametrize("executor", executors)
def test_argument_object(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert {"foo": 1} == executor(session, 
            "return arguments[0]", args=[{"foo": 1}])

globals = set([
              "document",
              "navigator",
              "window",
              ])
@pytest.mark.parametrize("executor", executors)
def test_access_todefault_globals(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    for property in globals:
        assert property == executor(session, 
            "return typeof arguments[0] != 'undefined' ? arguments[0] : null",
            args=[property])


@pytest.mark.parametrize("executor", executors)
def test_return_web_element(session, executor):
    session.url = inline("""<body><p>Cheese""")
    expected = session.find.css("p", all=False)
    actual = executor(session, 
            "return document.querySelector('p')")
    assert_same_element(session, expected.json(), actual)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element_array(session, executor):
    session.url = inline("""<p>Cheese <p>Peas""")
    expected = session.find.css("p")
    actual = executor(session, """
            let els = document.querySelectorAll('p');
            return [els[0], els[1]]""")
    assert_elements_equal(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_return_web_element_nodelist(session, executor):
    session.url = inline("""<p>Peas <p>Cheese""")
    expected = session.find.css("p")
    actual = executor(session, "return document.querySelectorAll('p')")
    assert_elements_equal(session, expected, actual)


@pytest.mark.parametrize("executor", executors)
def test_sandbox_reuse(session, executor):
    session.url= inline("""<title>JS testing</title>""")
    executor(session, "window.foobar = [23, 42];")
    assert [23, 42] == executor(session, "return window.foobar")


@pytest.mark.parametrize("executor", executors)
def test_no_args(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    assert executor(session, 
        "return typeof arguments[0] == 'undefined'")


@pytest.mark.parametrize("executor", executors)
def test_toJSON(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    foo = executor(session, """
            return {
              toJSON () {
                return "foo";
              }
            }""")
    assert "foo" == foo


@pytest.mark.parametrize("executor", executors)
def test_unsafe_toJSON(session, executor):
    session.url = inline("""<title>JS testing</title>""")
    el = executor(session, """
            return {
              toJSON () {
                return document.documentElement;
              }
            }""")
    expected = executor(session, "return document.documentElement")
    assert_same_element(session, expected, el)


@pytest.mark.parametrize("executor", executors)
def test_html_all_collection(session, executor):
    session.url = inline("<p>foo <p>bar")
    els = executor(session, "return document.all")

    # <html>, <head>, <body>, <p>, <p>
    assert 5 == len(els)


@pytest.mark.parametrize("executor", executors)
def test_html_form_controls_collection(session, executor):
    session.url = inline("<form><input><input></form>")
    actual = executor(session, "return document.forms[0].elements")
    expected = session.find.css("input")
    assert_elements_equal(session, expected, actual)

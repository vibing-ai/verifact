# Verifact Linting Issues

## Summary

Total issues found: 274

## Issues by Rule

| Rule | Count | Example |
|------|-------|-------------|
| W293 | 61 | Blank line contains whitespace |
| B904 | 50 | Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling |
| D107 | 31 | Missing docstring in `__init__` |
| D415 | 26 | First line should end with a period, question mark, or exclamation point |
| B008 | 20 | Do not perform function call `Body` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable |
| F403 | 20 | `from .agents import *` used; unable to detect undefined names |
| F841 | 17 | Local variable `version_parser` is assigned to but never used |
| D102 | 9 | Missing docstring in public method |
| W291 | 8 | Trailing whitespace |
| D205 | 8 | 1 blank line required between summary line and description |
| E722 | 4 | Do not use bare `except` |
| D105 | 4 | Missing docstring in magic method |
| F811 | 3 | Redefinition of unused `datetime` from line 7 |
| B007 | 2 | Loop control variable `claim_id` not used within loop body |
| F821 | 2 | Undefined name `ApiKeyScope` |
| C401 | 2 | Unnecessary generator (rewrite as a set comprehension) |
| F401 | 2 | `psycopg2.extras.execute_values` imported but unused; consider using `importlib.util.find_spec` to test for availability |
| C419 | 1 | Unnecessary list comprehension |
| D101 | 1 | Missing docstring in public class |
| B039 | 1 | Do not use mutable data structures for `ContextVar` defaults |
| B019 | 1 | Use of `functools.lru_cache` or `functools.cache` on methods can lead to memory leaks |
| D417 | 1 | Missing argument description in the docstring for `call`: `**kwargs` |

## Issues by File

### src/api/admin.py (35 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 8:22** - F811: Redefinition of unused `datetime` from line 7
- **Line 133:1** - W293: Blank line contains whitespace
- **Line 135:1** - W293: Blank line contains whitespace
- **Line 140:30** - B008: Do not perform function call `Body` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 140:65** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 165:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 177:1** - W293: Blank line contains whitespace
- **Line 179:1** - W293: Blank line contains whitespace
- **Line 183:56** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 196:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 208:1** - W293: Blank line contains whitespace
- **Line 210:1** - W293: Blank line contains whitespace
- **Line 214:56** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 229:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 233:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 245:1** - W293: Blank line contains whitespace
- **Line 247:1** - W293: Blank line contains whitespace
- **Line 251:59** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 259:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 272:1** - W293: Blank line contains whitespace
- **Line 274:1** - W293: Blank line contains whitespace
- **Line 279:62** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 281:5** - D205: 1 blank line required between summary line and description
- **Line 320:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 332:1** - W293: Blank line contains whitespace
- **Line 334:1** - W293: Blank line contains whitespace
- **Line 338:48** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 366:1** - W293: Blank line contains whitespace
- **Line 368:1** - W293: Blank line contains whitespace
- **Line 373:59** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 407:1** - W293: Blank line contains whitespace
- **Line 409:1** - W293: Blank line contains whitespace
- **Line 413:52** - B008: Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 423:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/utils/validation/exceptions.py (20 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 13:9** - D107: Missing docstring in `__init__`
- **Line 37:9** - D107: Missing docstring in `__init__`
- **Line 55:9** - D107: Missing docstring in `__init__`
- **Line 69:9** - D107: Missing docstring in `__init__`
- **Line 86:9** - D107: Missing docstring in `__init__`
- **Line 103:9** - D107: Missing docstring in `__init__`
- **Line 121:9** - D107: Missing docstring in `__init__`
- **Line 143:9** - D107: Missing docstring in `__init__`
- **Line 161:9** - D107: Missing docstring in `__init__`
- **Line 177:9** - D107: Missing docstring in `__init__`
- **Line 196:9** - D107: Missing docstring in `__init__`
- **Line 208:9** - D107: Missing docstring in `__init__`
- **Line 222:9** - D107: Missing docstring in `__init__`
- **Line 238:9** - D107: Missing docstring in `__init__`
- **Line 256:9** - D107: Missing docstring in `__init__`
- **Line 274:9** - D107: Missing docstring in `__init__`
- **Line 284:9** - D107: Missing docstring in `__init__`
- **Line 291:9** - D107: Missing docstring in `__init__`
- **Line 307:9** - D107: Missing docstring in `__init__`

### src/api/feedback.py (16 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 124:1** - W293: Blank line contains whitespace
- **Line 127:1** - W293: Blank line contains whitespace
- **Line 132:1** - W293: Blank line contains whitespace
- **Line 182:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 187:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 193:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 204:1** - W293: Blank line contains whitespace
- **Line 212:48** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 231:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 243:1** - W293: Blank line contains whitespace
- **Line 252:23** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 262:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 274:1** - W293: Blank line contains whitespace
- **Line 282:69** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 301:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/cli.py (16 issues)

- **Line 2:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 27:26** - F811: Redefinition of unused `PipelineConfig` from line 25
- **Line 148:5** - F841: Local variable `version_parser` is assigned to but never used
- **Line 425:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 433:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 435:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 470:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 476:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 563:13** - F841: Local variable `stats` is assigned to but never used
- **Line 664:25** - C401: Unnecessary generator (rewrite as a set comprehension)
- **Line 676:21** - C401: Unnecessary generator (rewrite as a set comprehension)
- **Line 880:17** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 886:17** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 895:17** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 913:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 926:13** - F841: Local variable `use_color` is assigned to but never used

### src/agents/claim_detector/detector.py (15 issues)

- **Line 114:1** - W293: Blank line contains whitespace
- **Line 123:1** - W293: Blank line contains whitespace
- **Line 129:1** - W293: Blank line contains whitespace
- **Line 136:1** - W293: Blank line contains whitespace
- **Line 138:95** - W291: Trailing whitespace
- **Line 140:1** - W293: Blank line contains whitespace
- **Line 147:1** - W293: Blank line contains whitespace
- **Line 155:1** - W293: Blank line contains whitespace
- **Line 161:1** - W293: Blank line contains whitespace
- **Line 166:1** - W293: Blank line contains whitespace
- **Line 172:1** - W293: Blank line contains whitespace
- **Line 175:1** - W293: Blank line contains whitespace
- **Line 212:1** - W293: Blank line contains whitespace
- **Line 218:1** - W293: Blank line contains whitespace
- **Line 235:1** - W293: Blank line contains whitespace

### src/api/factcheck.py (13 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 173:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 184:1** - W293: Blank line contains whitespace
- **Line 188:1** - W293: Blank line contains whitespace
- **Line 193:1** - W293: Blank line contains whitespace
- **Line 200:72** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 316:1** - W293: Blank line contains whitespace
- **Line 324:23** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 391:57** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 445:23** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 472:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 484:62** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 514:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/utils/db/users.py (13 issues)

- **Line 27:9** - F841: Local variable `user_data` is assigned to but never used
- **Line 33:9** - F841: Local variable `query` is assigned to but never used
- **Line 48:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 64:9** - F841: Local variable `query` is assigned to but never used
- **Line 92:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 116:9** - F841: Local variable `query` is assigned to but never used
- **Line 127:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 143:9** - F841: Local variable `query` is assigned to but never used
- **Line 151:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 168:9** - F841: Local variable `query` is assigned to but never used
- **Line 180:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 196:9** - F841: Local variable `query` is assigned to but never used
- **Line 207:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/agents/verdict_writer/writer.py (11 issues)

- **Line 91:1** - W293: Blank line contains whitespace
- **Line 99:1** - W293: Blank line contains whitespace
- **Line 108:1** - W293: Blank line contains whitespace
- **Line 115:1** - W293: Blank line contains whitespace
- **Line 120:1** - W293: Blank line contains whitespace
- **Line 125:1** - W293: Blank line contains whitespace
- **Line 132:1** - W293: Blank line contains whitespace
- **Line 269:13** - E722: Do not use bare `except`
- **Line 389:1** - W293: Blank line contains whitespace
- **Line 392:1** - W293: Blank line contains whitespace
- **Line 398:1** - W293: Blank line contains whitespace

### src/agents/evidence_hunter/hunter.py (10 issues)

- **Line 72:1** - W293: Blank line contains whitespace
- **Line 78:1** - W293: Blank line contains whitespace
- **Line 84:1** - W293: Blank line contains whitespace
- **Line 90:1** - W293: Blank line contains whitespace
- **Line 96:1** - W293: Blank line contains whitespace
- **Line 132:1** - W293: Blank line contains whitespace
- **Line 134:1** - W293: Blank line contains whitespace
- **Line 140:1** - W293: Blank line contains whitespace
- **Line 170:9** - D205: 1 blank line required between summary line and description
- **Line 191:9** - D205: 1 blank line required between summary line and description

### src/utils/db/db.py (10 issues)

- **Line 25:45** - F401: `psycopg2.extras.execute_values` imported but unused; consider using `importlib.util.find_spec` to test for availability
- **Line 225:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 251:17** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 319:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 1021:47** - F821: Undefined name `Feedback`
- **Line 1045:13** - F841: Local variable `metadata` is assigned to but never used
- **Line 1090:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 1142:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 1214:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 1391:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/api/factcheck_batch.py (9 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 173:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 278:1** - W293: Blank line contains whitespace
- **Line 282:1** - W293: Blank line contains whitespace
- **Line 291:23** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 377:1** - W293: Blank line contains whitespace
- **Line 391:23** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 464:59** - B008: Do not perform function call `Security` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
- **Line 501:13** - B007: Loop control variable `claim_id` not used within loop body

### src/utils/models/model_config.py (9 issues)

- **Line 91:9** - D107: Missing docstring in `__init__`
- **Line 112:9** - D107: Missing docstring in `__init__`
- **Line 169:20** - B007: Loop control variable `default` not used within loop body
- **Line 371:5** - B019: Use of `functools.lru_cache` or `functools.cache` on methods can lead to memory leaks
- **Line 495:73** - F841: Local variable `request_id` is assigned to but never used
- **Line 683:73** - F841: Local variable `request_id` is assigned to but never used
- **Line 921:45** - F401: `openai._base_client.DEFAULT_MAX_RETRIES` imported but unused; consider using `importlib.util.find_spec` to test for availability
- **Line 952:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 988:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/tests/__init__.py (7 issues)

- **Line 23:1** - F403: `from .agents import *` used; unable to detect undefined names
- **Line 24:1** - F403: `from .api import *` used; unable to detect undefined names
- **Line 25:1** - F403: `from .integration import *` used; unable to detect undefined names
- **Line 26:1** - F403: `from .models import *` used; unable to detect undefined names
- **Line 27:1** - F403: `from .performance import *` used; unable to detect undefined names
- **Line 28:1** - F403: `from .system import *` used; unable to detect undefined names
- **Line 29:1** - F403: `from .utils import *` used; unable to detect undefined names

### src/api/middleware.py (6 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 71:9** - D107: Missing docstring in `__init__`
- **Line 248:9** - D107: Missing docstring in `__init__`
- **Line 404:9** - D107: Missing docstring in `__init__`
- **Line 462:67** - F821: Undefined name `ApiKeyScope`
- **Line 482:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/config.py (6 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 63:9** - D102: Missing docstring in public method
- **Line 87:9** - D102: Missing docstring in public method
- **Line 117:9** - D102: Missing docstring in public method
- **Line 177:9** - D102: Missing docstring in public method
- **Line 203:9** - D415: First line should end with a period, question mark, or exclamation point

### src/tests/performance/conftest.py (6 issues)

- **Line 31:109** - W291: Trailing whitespace
- **Line 35:111** - W291: Trailing whitespace
- **Line 36:111** - W291: Trailing whitespace
- **Line 39:108** - W291: Trailing whitespace
- **Line 40:107** - W291: Trailing whitespace
- **Line 41:106** - W291: Trailing whitespace

### src/utils/logging/structured_logger.py (6 issues)

- **Line 27:9** - D107: Missing docstring in `__init__`
- **Line 49:9** - D102: Missing docstring in public method
- **Line 110:9** - D107: Missing docstring in `__init__`
- **Line 115:9** - D105: Missing docstring in magic method
- **Line 132:9** - D105: Missing docstring in magic method
- **Line 141:9** - D107: Missing docstring in `__init__`

### src/utils/db/api_keys.py (5 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 63:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 69:5** - D205: 1 blank line required between summary line and description
- **Line 161:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 364:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/tests/agents/__init__.py (4 issues)

- **Line 11:1** - F403: `from .test_agent_detector import *` used; unable to detect undefined names
- **Line 12:1** - F403: `from .test_claim_detector import *` used; unable to detect undefined names
- **Line 13:1** - F403: `from .test_evidence_hunter import *` used; unable to detect undefined names
- **Line 14:1** - F403: `from .test_verdict_writer import *` used; unable to detect undefined names

### src/utils/logging/logger.py (4 issues)

- **Line 38:13** - D102: Missing docstring in public method
- **Line 128:87** - B039: Do not use mutable data structures for `ContextVar` defaults
- **Line 145:9** - D102: Missing docstring in public method
- **Line 191:9** - D102: Missing docstring in public method

### src/agents/examples/pipeline_testing.py (3 issues)

- **Line 19:9** - D107: Missing docstring in `__init__`
- **Line 48:9** - D107: Missing docstring in `__init__`
- **Line 67:9** - D107: Missing docstring in `__init__`

### src/pipeline/factcheck_pipeline.py (3 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 278:85** - F841: Local variable `timer` is assigned to but never used
- **Line 324:85** - F841: Local variable `timer` is assigned to but never used

### src/tests/agents/test_agent_detector.py (3 issues)

- **Line 33:7** - D101: Missing docstring in public class
- **Line 36:9** - D415: First line should end with a period, question mark, or exclamation point
- **Line 126:9** - F841: Local variable `results` is assigned to but never used

### src/tests/integration/__init__.py (3 issues)

- **Line 10:1** - F403: `from .test_db_integration import *` used; unable to detect undefined names
- **Line 11:1** - F403: `from .test_factcheck_pipeline import *` used; unable to detect undefined names
- **Line 12:1** - F403: `from .test_pipeline_integration import *` used; unable to detect undefined names

### src/tests/utils/__init__.py (3 issues)

- **Line 10:1** - F403: `from .test_db_utils import *` used; unable to detect undefined names
- **Line 11:1** - F403: `from .test_model_config import *` used; unable to detect undefined names
- **Line 12:1** - F403: `from .test_search_tools import *` used; unable to detect undefined names

### src/utils/error_handling.py (3 issues)

- **Line 17:5** - D415: First line should end with a period, question mark, or exclamation point
- **Line 19:9** - D107: Missing docstring in `__init__`
- **Line 33:5** - D415: First line should end with a period, question mark, or exclamation point

### src/utils/security/encrypted_fields.py (3 issues)

- **Line 17:9** - D105: Missing docstring in magic method
- **Line 21:9** - D102: Missing docstring in public method
- **Line 28:9** - D105: Missing docstring in magic method

### src/utils/security/encryption.py (3 issues)

- **Line 35:13** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 77:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 97:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/agents/claim_detector/utils.py (2 issues)

- **Line 214:9** - D415: First line should end with a period, question mark, or exclamation point
- **Line 221:9** - E722: Do not use bare `except`

### src/main.py (2 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 56:82** - W291: Trailing whitespace

### src/models/factcheck.py (2 issues)

- **Line 140:17** - E722: Do not use bare `except`
- **Line 534:7** - F811: Redefinition of unused `FactcheckJob` from line 373

### src/tests/api/test_api.py (2 issues)

- **Line 2:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 131:9** - E722: Do not use bare `except`

### src/utils/db/pool.py (2 issues)

- **Line 36:5** - D205: 1 blank line required between summary line and description
- **Line 75:5** - D205: 1 blank line required between summary line and description

### src/utils/validation/sanitizer.py (2 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point
- **Line 35:5** - D205: 1 blank line required between summary line and description

### src/utils/validation/validation.py (2 issues)

- **Line 47:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
- **Line 227:9** - B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

### src/__init__.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point

### src/models/feedback.py (1 issues)

- **Line 91:13** - C419: Unnecessary list comprehension

### src/tests/agents/test_evidence_hunter.py (1 issues)

- **Line 40:66** - F841: Local variable `mock_agent` is assigned to but never used

### src/tests/api/__init__.py (1 issues)

- **Line 7:1** - F403: `from .test_api import *` used; unable to detect undefined names

### src/tests/performance/__init__.py (1 issues)

- **Line 7:1** - F403: `from .test_benchmark_pipeline import *` used; unable to detect undefined names

### src/tests/system/__init__.py (1 issues)

- **Line 7:1** - F403: `from .test_verifact import *` used; unable to detect undefined names

### src/tests/system/test_verifact.py (1 issues)

- **Line 2:1** - D415: First line should end with a period, question mark, or exclamation point

### src/ui/app.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point

### src/ui/events.py (1 issues)

- **Line 24:5** - D205: 1 blank line required between summary line and description

### src/utils/async/priority_queue.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point

### src/utils/async/retry.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point

### src/utils/rate_limiter.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point

### src/utils/search/search_tools.py (1 issues)

- **Line 70:15** - D417: Missing argument description in the docstring for `call`: `**kwargs`

### src/utils/validation/config.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point

### src/utils/validation/validator.py (1 issues)

- **Line 1:1** - D415: First line should end with a period, question mark, or exclamation point


import copy
import logging

from alpha_codium.gen.stages.indirect.run_analyze_and_fix_test_failure import run_analyze_and_fix_test_failure
from alpha_codium.gen.stages.run_tests import run_tests
from alpha_codium.log import get_logger
from alpha_codium.settings.config_loader import get_settings

logger = get_logger(__name__)


async def run_evaluate_all_ai_tests(self, problem):
    try:
        logger.info("--iterate on all ai tests stage--")
        ai_tests = problem['problem_ai_tests']
        max_allowed_calls = get_settings().get("ai_tests.max_allowed_calls", 6)
        public_tests_passed = len(problem['passed_tests']['inputs'])
        # evaluate ai tests
        actual_number_of_calls = 0
        last_code_solution = ''

        for actual_number_of_calls in range(max_allowed_calls):

            failing_tests_inputs = []
            failing_tests_outputs = []
            failing_tests_errors = []
            passed_tests_inputs = []
            passed_tests_outputs = []
            error_string_for_fix = ''

            for i, test in enumerate(ai_tests):
                counter = 0
                test_inputs = test['input']
                test_outputs = test['output']
                if not isinstance(test_inputs, list):
                    test_inputs = [test_inputs]
                    test_outputs = [test_outputs]

                # run the solution on the tests
                problem, test_passed, non_empty_output, error_str, trace_str, tests_timeout, d_tot \
                    = run_tests(self, problem, counter, test_inputs, test_outputs)

                # we passed without changing the code. Add the test to the passed tests list
                if test_passed:
                    passed_tests_inputs += test_inputs
                    passed_tests_outputs += test_outputs
                else:
                    failing_tests_inputs += test_inputs
                    failing_tests_outputs += test_outputs
                    failing_tests_errors.append(error_str)

            for i, inputs in enumerate(failing_tests_inputs):
                if inputs in problem['passed_tests']['inputs']:
                    logger.info(f"Test {i} failed, but passed before. reverting to last solution")
                    problem['code_recent_solution'] = last_code_solution
                    break
            
            if not problem['code_recent_solution'] == last_code_solution:
                for i, inputs in enumerate(passed_tests_inputs):
                    if not inputs in problem['passed_tests']['inputs']:
                        logger.info(f"Test {i} passed after fixing code. adding to passed tests")
                        problem['passed_tests']['inputs'] += inputs
                        problem['passed_tests']['outputs'] += passed_tests_outputs[i]

            if len(failing_tests_inputs) == 0:
                logger.info(f"Passed all ai tests. exiting the stage")
                break

            error_string_for_fix = failing_tests_errors[0]


            ai_tests_passed = len(problem['passed_tests']['inputs']) - public_tests_passed
            ai_tests_failed = len(ai_tests) - ai_tests_passed
            
            logger.info(f'Passed {ai_tests_passed} out of {len(ai_tests)} ai tests at rev {actual_number_of_calls}')
            
            if ai_tests_passed == len(ai_tests):
                logger.info(f"Passed all ai tests. exiting the stage")
                break
            
            logger.error(f"Failed to pass ai tests. trying to fix code")

            # run 'analyze_and_fix_test_failure' stage
            actual_number_of_calls += 1

            problem['number_of_llm_fixes_ai'] = actual_number_of_calls
            if actual_number_of_calls < max_allowed_calls - 1:
                problem = await run_analyze_and_fix_test_failure(self, problem, error_string_for_fix)
                logger.info(f"attempt {actual_number_of_calls} out of {max_allowed_calls}")

        problem['ai_tests_total'] = len(ai_tests)
        problem['ai_tests_passed'] = len(problem['passed_tests']['inputs']) - public_tests_passed

        return problem
    except Exception as e:
        logging.error(f"Error in 'run_evaluate_all_ai_tests': {e}")
        return problem

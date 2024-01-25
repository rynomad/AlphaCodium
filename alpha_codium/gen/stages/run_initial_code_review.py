import copy
import logging

from alpha_codium.settings.config_loader import get_settings
from alpha_codium.gen.stages.run_initial_solve import run_initial_solve
from alpha_codium.gen.stages.run_tests import run_tests
from alpha_codium.log import get_logger

logger = get_logger(__name__)


async def run_initial_code_review(self, problem):
    counter_retry = 0
    while True:
        try:
            logger.info("--run initial code review stage--")

            max_attempts = get_settings().get('initial_code_review.iterations', 5)
            counter = 0

            for i in range(max_attempts):
                f = functools.partial(self._run, problem=problem, prompt="code_contests_prompt_initial_code_review")
                response_solve, _ = await send_inference(f)

                # clean up the response
                response_solve = response_solve.rstrip("` \n")
                if response_solve.startswith("```python"):
                    response_solve = response_solve[10:]
                elif response_solve.startswith("python"):
                    response_solve = response_solve[6:]
                # generate an initial code, using the top solution from the previous stage

                problem['code_recent_solution'] = response_solve
                problem['code_prev_solution'] = response_solve
            return problem
        except Exception as e:
            logging.error(f"'initial code generation' stage, counter_retry {counter_retry}, Error: {e}")
            counter_retry += 1
            if counter_retry > 2:
                raise e

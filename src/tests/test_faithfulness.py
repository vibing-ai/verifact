import pytest
from deepeval.evaluate import evaluate
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

from src.verifact_manager import VerifactManager

load_dotenv()

def validate_metric(metric_data, expect_success, min_score):
    assert metric_data.score > min_score, "Score should be greater than specified in the test data"
    assert metric_data.success is expect_success
    assert metric_data.reason is not None
    assert "Truths" in metric_data.verbose_logs
    assert "Claims" in metric_data.verbose_logs
    assert "Verdicts" in metric_data.verbose_logs
    print(f"metric reason: {metric_data.reason}")
    print(f"verbose logs: {metric_data.verbose_logs}")
@pytest.mark.asyncio
async def test_faithfulness_real_output(query, expect_success, min_score):
    """Test the faithfulness.

    :param query: test question
    :param expect_success: expected success [True, False]
    :param min_score: min score expected
    :assert metric_data.score > min_score, score should be greater than specified in the test data
    :assert metric_data.success is expect_success
    :assert metric_data.reason is not None
    :assert "Truths" in metric_data.verbose_logs, Truths exists:
    :assert "Claims" in metric_data.verbose_logs, Claims exists
    :assert "Verdicts" in metric_data.verbose_logs, Verdicts have been given
    """
    manager = VerifactManager()

    results = await manager.run(query)
    assert results, "No output from VerifactManager."

    for _claim, evidence_list, verdict in results:
        if not verdict or not evidence_list:
            continue

        test_case = LLMTestCase(
            input=query,
            actual_output=verdict.explanation,
            retrieval_context = [str(ev.content) for ev in evidence_list if ev.content]
            )

        metric = FaithfulnessMetric(
            include_reason=True, strict_mode=True
            )

        evaluation_results = evaluate(test_cases=[test_case], metrics=[metric])

        for result in evaluation_results:

            _, test_result_list = result

            if not test_result_list:
                continue
            for test_result in test_result_list:
                print(f"Test Result list name: {test_result.name}")
                for metric_data in test_result.metrics_data:
                    validate_metric(metric_data, expect_success, min_score)
                        # assert metric_data.score > min_score, "Score should be greater than specified in the test data"
                        # assert metric_data.success is expect_success
                        # assert metric_data.reason is not None
                        # assert "Truths" in metric_data.verbose_logs
                        # assert "Claims" in metric_data.verbose_logs
                        # assert "Verdicts" in metric_data.verbose_logs
                        # print(f"metric reason: {metric_data.reason}")
                        # print(f"verbose logs: {metric_data.verbose_logs}")
            else:
                print(f"Test Result {test_result.name} list is None or empty")

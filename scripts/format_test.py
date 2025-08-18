from pathlib import Path


class TestFormatting:
    def test_format_for_my_ugliest_function(self):
        return (
            Path(__file__).parent.parent.parent
            / "data"
            / "golden_tables"
            / "DateType_Date&Time_Alignment_GT"
            / "WEEK"
            / "DateType_Replacement_WEEK_Date&Time_Alignment_Output.csv"
        )

    def empty_function(self):
        pass

    def test_path_construction_with_bad_formatting(self):
        expected_path = (
            Path(__file__).parent.parent
            / ".github"
            / "golden_tables"
            / "DateType_Date&Time_Alignment_GT"
            / "WEEK"
            / "DateType_Replacement_WEEK_Date&Time_Alignment_Output.csv"
        )

        result = self.test_format_for_my_ugliest_function()

        assert result == expected_path, f"Expected {expected_path} but got {result}"

    def test_empty_function_with_horrible_spacing(self):
        result = self.empty_function()

        assert result is None, "Empty function should return None"

    def test_with_extremely_long_line_that_definitely_violates_pep8_and_will_make_ruff_very_unhappy_because_its_way_too_long(
        self,
    ):
        path = self.test_format_for_my_ugliest_function()
        assert isinstance(path, Path), (
            "The function should return a Path object but it returned something else which is definitely not what we expected"
        )

    def test_mixed_quotes(self):
        path = self.test_format_for_my_ugliest_function()
        assert str(path).endswith(
            "DateType_Replacement_WEEK_Date&Time_Alignment_Output.csv"
        ) and str(path).startswith(".github")

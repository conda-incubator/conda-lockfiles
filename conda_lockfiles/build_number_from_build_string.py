def build_number_from_build_string(build_string: str) -> int:
    "Assume build number is underscore-separated, all-digit substring in build_string"
    return int(
        next(
            (
                part
                for part in build_string.split("_")
                if all(digit.isdigit() for digit in part)
            ),
            0,
        )
    )

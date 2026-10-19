from compare.measure import measure


# Sanity check: REST and GraphQL return the same data for each screen, so the comparison is fair.
def test_both_styles_return_the_same_facts():
    for screen, styles in measure().items():
        assert styles["REST"].data == styles["GraphQL"].data, screen


# GraphQL needs 1 request per screen, REST needs 2 (order, then shipment).
def test_graphql_needs_one_request_where_rest_needs_two():
    for screen, styles in measure().items():
        assert styles["REST"].requests == 2 and styles["GraphQL"].requests == 1, screen


# With few fields needed, GraphQL transfers less than a quarter of the bytes REST does.
def test_graphql_saves_most_bytes_when_the_client_needs_few_fields():
    status = measure()["A. status line (2 fields)"]
    assert status["GraphQL"].total < status["REST"].total * 0.25


# When the client needs everything, GraphQL has no byte advantage (the query text adds overhead).
def test_graphql_saves_no_bytes_when_the_client_needs_everything():
    detail = measure()["B. detail screen (all fields)"]
    # The query text is sent as well, so the total can even exceed REST's.
    assert detail["GraphQL"].total >= detail["REST"].total

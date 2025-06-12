# @pytest.mark.django_db
# def test_circular_merge_chain_detection_prevents_infinite_recursion():
#     user = User.objects.create_user(username="victim_user", password="pass123")

#     identity_a = Identity.objects.create(linked_user=user)

#     identity_b = Identity.objects.create(linked_user=user)

#     identity_c = Identity.objects.create(linked_user=user)

#     Touchpoint.objects.create(
#         identity=identity_a,
#         url="https://site.com/page-a",
#         utm_source="google",
#         utm_campaign="campaign_a",
#     )

#     Touchpoint.objects.create(
#         identity=identity_b,
#         url="https://site.com/page-b",
#         utm_source="facebook",
#         utm_campaign="campaign_b",
#     )

#     Touchpoint.objects.create(
#         identity=identity_c,
#         url="https://site.com/page-c",
#         utm_source="email",
#         utm_campaign="campaign_c",
#     )

#     identity_a.merged_into = identity_b  # A → B
#     identity_b.merged_into = identity_c  # B → C
#     identity_c.merged_into = identity_a  # C → A (creates cycle: A→B→C→A)

#     identity_a.save()
#     identity_b.save()
#     identity_c.save()

#     assert identity_a.merged_into == identity_b
#     assert identity_b.merged_into == identity_c
#     assert identity_c.merged_into == identity_a

#     canonical_a: Optional[Identity] = identity_a.get_canonical_identity()
#     canonical_b: Optional[Identity] = identity_b.get_canonical_identity()
#     canonical_c: Optional[Identity] = identity_c.get_canonical_identity()

#     assert canonical_a == canonical_b == canonical_c

#     assert canonical_a in [identity_a, identity_b, identity_c]

#     assert canonical_a is not None
#     assert isinstance(canonical_a, Identity)

#     canonical_a.touchpoints.all()

#     assert canonical_a.uuid is not None
#     assert canonical_a.linked_user == user

#     for _ in range(5):
#         result = identity_a.get_canonical_identity()
#         assert result == canonical_a

#     for identity in [identity_a, identity_b, identity_c]:
#         assert identity.get_canonical_identity() == canonical_a

#     assert canonical_a.is_canonical() is True

#     canonical_chain_length = 0
#     current: Optional[Identity] = canonical_a
#     visited = set()

#     while current and current.id not in visited and canonical_chain_length < 10:
#         visited.add(current.id)
#         current = current.merged_into
#         canonical_chain_length += 1

#     assert canonical_a.merged_into is None or canonical_chain_length < 10

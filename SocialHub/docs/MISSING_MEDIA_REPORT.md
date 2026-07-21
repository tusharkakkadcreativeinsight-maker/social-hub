# Missing Media Report

Generated: 2026-07-14

This report was produced by python scripts/media_audit.py in dry-run mode. No database rows or files were deleted or modified.

## Summary

- Missing media references detected: 31
- Exact safe matches found in current uploads tree: 0 in sampled output
- Action taken: unresolved references documented only
- Required UI behavior: use /uploads/<relative-path> for present media and a local media-unavailable fallback for unresolved paths.

## Raw Dry-Run Output

``text
missing_count=31
{'table': 'reels', 'id': 'adc67fb8-ff1b-4509-b98a-89334920096d', 'field': 'video_url', 'path': 'reels/0b880e3a40c14f279caa7db1abebd9df.mp4', 'candidate_matches': []}
{'table': 'stories', 'id': '474804c5-f15b-487a-9c8d-780b9a4a077d', 'field': 'media_url', 'path': 'stories/f36b961f51d0452ea76cd154f04677d3.png', 'candidate_matches': []}
{'table': 'stories', 'id': '2c28b3ef-9982-426c-9cff-a0ad323fe2eb', 'field': 'media_url', 'path': 'stories/bffdb682ec734122abca8fad18998063.png', 'candidate_matches': []}
{'table': 'stories', 'id': 'eba369e3-cc87-40e3-a270-e4f514048169', 'field': 'media_url', 'path': 'stories/bca323e365604660b9abd8107bf47c5b.png', 'candidate_matches': []}
{'table': 'stories', 'id': 'fef045f0-df48-4ea8-a29f-866afc1f4936', 'field': 'media_url', 'path': 'stories/46619902c20e453fb0a3a9dcefba183f.png', 'candidate_matches': []}
{'table': 'stories', 'id': 'f67a22c6-7a76-4b27-8438-364a7d65e5a1', 'field': 'media_url', 'path': 'stories/872b83ffc95a47af96b6b718903e8779.png', 'candidate_matches': []}
{'table': 'stories', 'id': '7c9512b9-f38e-4822-afbc-66d80ed81c2b', 'field': 'media_url', 'path': 'stories/05ae40ee3e394bb6bc653bc616591e3e.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '47a999b5-3695-4d9d-9d91-69aca24f4124', 'field': 'profile_picture', 'path': 'profiles/e3823dc660094690848f55724fea4b0a.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '1064a68c-7a1f-41c9-a47c-ee86afe36aa7', 'field': 'profile_picture', 'path': 'profiles/e8ed97196a8149cb9024db3e7ed79dde.png', 'candidate_matches': []}
{'table': 'profiles', 'id': 'a196a0dd-a109-4c64-b5f0-db18f244be72', 'field': 'profile_picture', 'path': 'profiles/076988bf130640f4981384fec8330efa.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '1a83d4a2-5a96-4e92-ab0b-70e1c5639f33', 'field': 'profile_picture', 'path': 'profiles/038481e2a1d84c93b7c6cafd90c2affd.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '2257d93d-e8a7-4a7f-9787-2d02822aec69', 'field': 'profile_picture', 'path': 'profiles/246eb62d3a324eed87e3d4eef674f574.png', 'candidate_matches': []}
{'table': 'profiles', 'id': 'c6ffd8ae-d67b-47cd-b3ad-ac0b74fe960f', 'field': 'profile_picture', 'path': 'profiles/46e15b605a154ed38bef2f6f6aafca7b.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '47a999b5-3695-4d9d-9d91-69aca24f4124', 'field': 'cover_photo', 'path': 'covers/1a671f9726614ac4a0ebc0ef6de1a752.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '1064a68c-7a1f-41c9-a47c-ee86afe36aa7', 'field': 'cover_photo', 'path': 'covers/caaa018b07844de79be0b3a4555b979a.png', 'candidate_matches': []}
{'table': 'profiles', 'id': 'a196a0dd-a109-4c64-b5f0-db18f244be72', 'field': 'cover_photo', 'path': 'covers/e2bee44abf17425494ce134cac03de9e.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '1a83d4a2-5a96-4e92-ab0b-70e1c5639f33', 'field': 'cover_photo', 'path': 'covers/d53ec8ba8048428891f5a5c2f3d2cf36.png', 'candidate_matches': []}
{'table': 'profiles', 'id': '2257d93d-e8a7-4a7f-9787-2d02822aec69', 'field': 'cover_photo', 'path': 'covers/86aca26c073b44ebb70d8e34c070f1a3.png', 'candidate_matches': []}
{'table': 'profiles', 'id': 'c6ffd8ae-d67b-47cd-b3ad-ac0b74fe960f', 'field': 'cover_photo', 'path': 'covers/837e58d6d23d411b8d9a63c2d5eddc03.png', 'candidate_matches': []}
{'table': 'marketplace_products', 'id': '83b7870c-11f4-4d83-9478-2c99554793e9', 'field': 'image_url', 'path': 'marketplace/c37730ae4d794472bdbfcc513104de11.png', 'candidate_matches': []}
{'table': 'marketplace_products', 'id': '8c0ba199-8e98-492d-ac01-41770d307ce1', 'field': 'image_url', 'path': 'marketplace/ebecad55da134fe79605b4d7c40a62e5.png', 'candidate_matches': []}
{'table': 'marketplace_products', 'id': '59ff8b7c-da55-4184-b6f8-1ec431b14b76', 'field': 'image_url', 'path': 'marketplace/6c0fbe91e512400f8f18cfb64318aaca.png', 'candidate_matches': []}
{'table': 'marketplace_products', 'id': '16f8c300-77f5-45c9-a028-a1f39d5da9a0', 'field': 'image_url', 'path': 'marketplace/9503b69dedd34f1ea99d75787f239923.png', 'candidate_matches': []}
{'table': 'marketplace_products', 'id': '4d4067ab-dc92-42ec-9b2a-8c5028f7aff1', 'field': 'image_url', 'path': 'marketplace/f9c43f75efb0431a8742a93b00d5a61b.png', 'candidate_matches': []}
{'table': 'marketplace_products', 'id': '752cad7c-2b31-4d34-ade9-3e2eda5d44d6', 'field': 'image_url', 'path': 'marketplace/fdfd1c85b8cc4e06a3088dd558e7aaac.png', 'candidate_matches': []}
{'table': 'original_media_assets', 'id': 'cc408c3f-53ef-4568-8b21-ef53326948d2', 'field': 'file_path', 'path': 'original_media/386fb3f2-a476-4a56-b293-808fc859b294/58c88b4d-b4fe-42aa-ae3a-d2f12c3f5662.png', 'candidate_matches': []}
{'table': 'original_media_assets', 'id': 'b4b6d5af-6bbe-4b93-b703-45be6382eb2e', 'field': 'file_path', 'path': 'original_media/2a1f92cc-d321-4de0-9280-0b94843fa7c0/719c0469-9e9b-48f2-8c09-bffa23048471.png', 'candidate_matches': []}
{'table': 'original_media_assets', 'id': '42094ada-9649-4980-8178-b13bf3addbe4', 'field': 'file_path', 'path': 'original_media/e31306b6-2860-4235-b211-740a17f13e29/064bd771-6cc9-49da-b27a-1e770c266fa8.png', 'candidate_matches': []}
{'table': 'original_media_assets', 'id': 'e2be2989-8c56-450b-842b-b335dbba8ba1', 'field': 'file_path', 'path': 'original_media/24b80459-60e4-4d43-a3ea-af0fd0345d52/c5fdd224-f7d9-4386-a2dc-691498d32a25.png', 'candidate_matches': []}
{'table': 'original_media_assets', 'id': 'c482673b-c739-4433-bf5f-63cedc5d5eef', 'field': 'file_path', 'path': 'original_media/3eb7d53d-51cf-4b26-ad78-56d561ec2843/da866e7e-08b4-457f-b938-646253320151.png', 'candidate_matches': []}
{'table': 'original_media_assets', 'id': 'a15b1868-08d2-4e1f-ada2-1c74e9fa9ccf', 'field': 'file_path', 'path': 'original_media/692bfc06-2450-4bf8-ac5b-912347e95c2c/72cf42e5-3a91-4619-923b-db3284caa04b.png', 'candidate_matches': []}

``

# SocialHub Audit Contract Snapshot

Generated from the existing project during the current repair pass. This is a
living contract map: it records verified structure and the known gaps that still
need gradual hardening without replacing the existing FastAPI/SQLAlchemy/HTML/CSS/JS architecture.

## Verified inventory

- Backend decorated routes discovered: **309**
- Browser frontend routes in `backend/main.py`: **36**
- HTML templates in `frontend/templates`: **32**
- JavaScript named function declarations in `frontend/static/js/app.js`: **182**
- Duplicate named JavaScript function declarations found by audit: **0**
- Inline event-handler attributes still present across templates: **153**
- Jinja templates are rendered through `Jinja2Templates.TemplateResponse` via `serve_html()`.
- Missing Phase-2 routes now exist: `/ai-creator-studio`, `/collections`, `/live`, `/music-library`.
- Upload storage contract is relative DB paths with public URLs under `/uploads/<relative-path>`.

## Endpoint contract map pattern

| Frontend action | HTTP method | API path | Auth required | Request format | Response format | JavaScript function | Backend function | Tables used | Current status | Required fix |
|---|---:|---|---|---|---|---|---|---|---|---|
| Login | POST | `/api/auth/login` | No | JSON email/password | JWT token payload | `handleLogin` | `login` | users/sessions/login history | Working | Continue 2FA UX hardening |
| Register | POST | `/api/auth/register` | No | JSON user payload | JWT token payload | `handleRegister` | `register` | users/profiles/settings | Working | Add username availability UI |
| Refresh token | POST | `/api/auth/refresh` | Refresh token | JSON refresh token | rotated JWT payload | `refreshAccessToken` | `refresh_token` | refresh sessions | Working | Keep rotation tests expanding |
| Home feed | GET | `/api/posts` | Yes | query pagination | `{posts, pagination}`-style dict | `loadFeed` | `get_feed` | posts/post_images/users/likes/bookmarks | Working | More infinite-scroll polish |
| Create post | POST | `/api/posts` | Yes | multipart files/content | post object | `handleCreatePost` | `create_post` | posts/post_images | Working | Continue reducing inline handlers |
| Reels feed | GET | `/api/reels` | Yes | query pagination | `{reels,...}` | `loadReels` | `get_reels` | reels/users/music | Working | Further lazy/preload tuning |
| Upload reel | POST | `/api/reels/upload` | Yes | multipart video/metadata | `{success,reel}` | `handleCreateReel` | `upload_reel` | reels/music | Working | Add richer client-side scheduling UI |
| Stories | GET/POST | `/api/stories` | Yes | query / multipart | list or story object | `loadStories`, `handleCreateStory` | `get_stories`, `create_story` | stories/story_views | Working | More sticker/poll UI integration |
| Chat list/messages | GET/POST | `/api/chats...` | Yes | JSON/multipart | chat/message objects | `loadChats`, `sendMessage` | messaging router | chats/messages/users | Working | Add reconnect/backoff metrics |
| Notifications | GET/PUT | `/api/notifications...` | Yes | query/none | notification objects | `loadNotifications` | notifications router | notifications/settings | Working | Do not claim real push provider without configuration |
| Search | GET | `/api/search` | Yes | query `q/type` | search result object | `handleSearch` | `search` | users/posts/reels/hashtags | Working | Add AbortController/debounce everywhere |
| Music library | GET/POST/PATCH/DELETE | `/api/music...` | Mixed | JSON/multipart | music objects | `loadMusicLibraryPage`, `uploadMusic` | music router | music/reels | Working | Expand ownership UI |
| Live session | POST/GET/WS | `/api/live...`, `/ws/live/{id}` | Yes for actions | JSON + websocket events | live objects/events | live helpers in `app.js` | live router/websocket | live_streams | Scoped working simulation | Document WebRTC/provider needed for true broadcast |
| Marketplace | GET/POST/DELETE | `/api/marketplace/products...` | Mixed | multipart/JSON | product objects | `loadMarketplacePage` | advanced router | marketplace_products | Working | Add edit/report/filter UI |
| Collaborations | GET/POST | `/api/collabs...` | Mixed | JSON | offer/application objects | `loadCollabsPage` | advanced router | collaboration_offers/applications | Working | Expand owner-management UI |
| Collections/saved | GET/POST/DELETE | `/api/collections...` | Yes | JSON | collection/item objects | `loadCollectionsPage` | collections router | collections/saved_items | Working | Add richer add/remove UX |
| Verification | GET/POST | `/api/verification...` | Yes/Admin | multipart/JSON | request/status | page JS + API client | verification router | verification_requests/audit | Working backend | Keep documents non-public |
| Wallet | GET/POST | `/api/wallet...` | Yes/Admin | JSON | wallet/payout data | page JS + API client | wallet router | wallet_transactions/payouts | Working backend | Keep demo earnings isolated |
| Admin | GET/POST | `/api/admin...` | Admin | query/JSON | admin objects | `loadAdminDashboard` | admin router | users/posts/reports/audit | Working | Continue canonical endpoint cleanup |

## Upload path contract

Database values must be relative paths only, for example:

- `posts/<filename>`
- `reels/<filename>`
- `stories/<filename>`
- `profiles/<filename>`
- `covers/<filename>`
- `music/<filename>`
- `chat/<filename>`
- `marketplace/<filename>`
- `original_media/<user-id>/<filename>`
- `live/<filename>`

Browser URLs must be generated as `/uploads/<relative-path>`. Absolute Windows
paths, `frontend/uploads/...`, `uploads/uploads/...`, and duplicated subfolders
are invalid. Existing startup repair normalizes legacy DB values in local DEBUG/AUTO_CREATE_TABLES mode.

## Current high-priority findings

1. The biggest remaining frontend debt is inline event handlers in legacy full-page templates.
2. `app.js` is still monolithic; safe delegated handlers were added, but full modular splitting remains a larger staged refactor.
3. `ui-refresh.css` is now consistently loaded by `base.html` and auto-injected by `app.js` for legacy templates.
4. Pytest is constrained to `backend/tests` and now uses a temp SQLite database plus temp upload directory.
5. Manual scripts such as `backend/test_api.py` still exist for manual smoke testing but are excluded by root `pytest.ini`.

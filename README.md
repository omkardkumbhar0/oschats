*   **User Authentication:**
    *   Login and Signup functionality (`login`, `signup`)
    *   Logout functionality (`logout`)
*   **Chat Functionality:**
    *   One-on-one messaging (`chat`)
    *   Real-time updates using polling (`pollMessages`)
    *   Display online status of users (`update_online_status`, `get_user_status`)
    *   Message timestamps
    *   Message replies (`replyToMessage`)
    *   Image and file uploads with preview (`previewFile`)
    *   Scroll to bottom on new messages (`scrollToBottom`)
    *   Highlighting replied-to messages (`highlightOriginalMessage`)
    *   Desktop notifications for new messages
    *   Mobile view (to use on phones)
*   **User Interface:**
    *   User list with online status indicators (`status-online`, `status-offline`)
    *   Profile photos
    *   Image preview modal (`openImageModal`)
    *   Responsive design (CSS styles in `chat.html`)
    *   Customizable message bubbles
    *   Smooth transitions and animations
*   **User Search:**
    *   Search users in the user list (`desktopSearchUsers`)
    *   Display search status and no results message
    *   Highlight search matches
*   **Admin Features (if the user is "OMKARKUMBHAR"):**
    *   Block users (`blockUser`)
    *   Ban users (`banUser`)
*   **Message Management:**
    *   Message deletion (`deleteMessage`)
    *   Multi-select message deletion
*   **Other:**
    *   Manage User Modal
    *   Database migrations (migrations/alembic.ini)
    *   Use of `timeago.js` library for "last seen" timestamps
    *   File size limit (20MB) for uploads
    *   Progress bar for file uploads
    *   Clear search functionality (`clearDesktopSearch`)

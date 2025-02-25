## 🚀 Features  

### 🔐 User Authentication  
- **Login & Signup** (`login`, `signup`)  
- **Logout** (`logout`)  

### 💬 Chat Functionality  
- **One-on-one messaging** (`chat`)  
- **Real-time updates** using polling (`pollMessages`)  
- **User online status** (`update_online_status`, `get_user_status`)  
- **Message timestamps**  
- **Message replies** (`replyToMessage`)  
- **Image & file uploads** with previews (`previewFile`)  
- **Auto-scroll to new messages** (`scrollToBottom`)  
- **Highlighted replies** (`highlightOriginalMessage`)  
- **Desktop notifications** for new messages  
- **Mobile-friendly UI**  

### 🎨 User Interface  
- **User list with online indicators** (`status-online`, `status-offline`)  
- **Profile photos**  
- **Image preview modal** (`openImageModal`)  
- **Responsive design** (`chat.html`)  
- **Customizable message bubbles**  
- **Smooth transitions & animations**  

### 🔎 User Search  
- **Search users in the list** (`desktopSearchUsers`)  
- **Search status & no results message**  
- **Highlight search matches**  
- **Clear search** (`clearDesktopSearch`)  

### 🛡️ Admin Features *(for user "OMKARKUMBHAR")*  
- **Block users** (`blockUser`)  
- **Ban users** (`banUser`)  

### ✉️ Message Management  
- **Delete messages** (`deleteMessage`)  
- **Multi-select message deletion**  

### ⚙️ Other Features  
- **Manage User Modal**  
- **Database migrations** (`migrations/alembic.ini`)  
- **"Last seen" timestamps** (`timeago.js` integration)  
- **File upload limit:** 20MB  
- **Upload progress bar**  

---

## 🛠 Installation  
If you're running this project for the first time after forking, install the dependencies:  

```bash
pip install Flask Flask-SQLAlchemy Werkzeug Flask-Migrate Flask-Login SQLAlchemy
```

![Screenshot 2025-02-25 202330](https://github.com/user-attachments/assets/d4ee9a5c-cd4b-4d6b-9cea-0120424a4a51)

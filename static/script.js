const sidebar = document.querySelector("#sidebar");
const hide_sidebar = document.querySelector(".hide-sidebar");
const new_chat_button = document.querySelector(".new-chat");

const user_menu = document.querySelector(".user-menu ul");
const show_user_menu = document.querySelector(".user-menu button");

show_user_menu.addEventListener("click", function() {
    if (user_menu.classList.contains("show")) {
        user_menu.classList.toggle("show");
        setTimeout(function() {
            user_menu.classList.toggle("show-animate");
        }, 200);
    } else {
        user_menu.classList.toggle("show-animate");
        setTimeout(function() {
            user_menu.classList.toggle("show");
        }, 50);
    }
});

const models = document.querySelectorAll(".model-selector button");

for (const model of models) {
    model.addEventListener("click", function() {
        document.querySelector(".model-selector button.selected")?.classList.remove("selected");
        model.classList.add("selected");
    });
}

const message_box = document.querySelector("#message");

message_box.addEventListener("keyup", function() {
    message_box.style.height = "auto";
    let height = message_box.scrollHeight + 2;
    if (height > 200) {
        height = 200;
    }
    message_box.style.height = height + "px";
});

function show_view(view_selector) {
    document.querySelectorAll(".view").forEach(view => {
        view.style.display = "none";
    });
//    document.querySelector(view_selector).scrollTop = document.querySelector(view_selector).scrollHeight;
    document.querySelector(view_selector).style.display = "flex";
    document.querySelector(view_selector).scrollTo({ top: document.querySelector(view_selector).scrollHeight, behavior: 'smooth' });
}

// New Chat Button Click Event
new_chat_button.addEventListener("click", function() {
    show_view(".new-chat-view");
    sessionStorage.removeItem('currentSessionId');  // Clear the current session ID
    document.querySelector('.conversation-view').innerHTML = '';  // Clear the message view
});

// Conversation Button Click Event
document.querySelectorAll(".conversation-button").forEach(button => {
    button.addEventListener("click", function() {
        const sessionId = button.getAttribute('data-session-id');

        fetch(`/chat_history?session_id=${sessionId}`)
        .then(response => response.json())
        .then(data => {
            const conversationView = document.querySelector('.conversation-view');
            conversationView.innerHTML = '';  // Clear the current view

            data.forEach(chat => {
                displayMessage(chat.sender, chat.message, chat.images);
            });
        });

        sessionStorage.setItem('currentSessionId', sessionId);  // Store the session ID
        show_view('.conversation-view');
    });
});

const messageInput = document.querySelector('.message-input');
const sendButton = document.querySelector('.send-button');

// Initialize send button as disabled
sendButton.disabled = true;

// Enable/disable the send button based on input value
messageInput.addEventListener('input', function() {
    if (messageInput.value.trim() !== '') {
        sendButton.disabled = false;
    } else {
        sendButton.disabled = true;
    }
});

// Prevent sending empty messages and handle message sending
sendButton.addEventListener('click', function(event) {
    if (messageInput.value.trim() === '') {
        event.preventDefault();
        sendButton.disabled = true;
        return;
    }

    let userMessage = messageInput.value;
    let currentSessionId = sessionStorage.getItem('currentSessionId');  // Retrieve the session ID
    console.log(currentSessionId);
    if (!currentSessionId) {
        // Create a new session if none exists
        fetch('/create_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            currentSessionId = data.session_id;
            sessionStorage.setItem('currentSessionId', currentSessionId);  // Store the new session ID
            addChatToHistory(currentSessionId);  // Add the new chat to the history
            sendMessage(currentSessionId, userMessage);  // Send the first message
            const logo = document.querySelector('.logo');
            logo.style.display = "none";

        })
        .catch(error => console.error('Error:', error));
    } else {
        sendMessage(currentSessionId, userMessage);
    }
});

function sendMessage(sessionId, userMessage, filename, document=false) {
    fetch('/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: sessionId,
            message: document ? `Uploaded: ${filename}` : userMessage,
            file_content: document ? userMessage : null,

        })
    })
    .then(response => response.json())
    .then(data => {
        messageInput.value = '';
        displayMessage('user', document ? `Uploaded: ${filename}` : userMessage);
        if (data.status === 'Message received, starting stream...') {
            if (document==true) {
            startStream(`${filename}`, sessionId, true);
            scrollToBottom();
            }
            else{
            startStream(userMessage, sessionId);  // Now open the SSE connection to stream the response
            scrollToBottom();
            }
        }
    })
    .catch(error => {
        console.error('Error during fetch:', error);
    });
}

const chatHistoryContainer = document.querySelector('.conversation-view');

    function startStream(userMessage, sessionId, doc=false) {
    const eventSource = new EventSource(`/stream_response?message=${encodeURIComponent(userMessage)}&session_id=${sessionId}&document=${doc}`);

    // Create a single message block for the assistant's response
    let messageContainer = createMessageContainer('assistant');
    let rawTextCache = '';  // Cache to store the full raw text as it comes in

    eventSource.onmessage = function(event) {
        if (event.data === '[DONE]') {
            eventSource.close();  // Close the stream once it's done
            return;
        }

        // Parse the JSON string received from the backend
        const parsedData = JSON.parse(event.data);

        if (parsedData.response) {
            const chunk = parsedData.response;
            rawTextCache += chunk;  // Append new raw text to the cache
            updateMessageContent(messageContainer, rawTextCache);  // Update text content
            scrollToBottom();
        } else if (parsedData.image) {
            // If the chunk contains an image, create an image element
            let img = document.createElement('img');
            img.src = `data:image/png;base64,${parsedData.image}`;
            img.style.maxWidth = '300px';  // Set a max width for better display
            messageContainer.appendChild(img);  // Append the image to the message container
            scrollToBottom();
        }
    };

    eventSource.onerror = function(error) {
        eventSource.close();  // Handle errors and close the stream
        console.error('Error:', error);
    };
}


        function createMessageContainer(sender) {
            // Create a container for a single assistant/user message
            let messageContainer = document.createElement('div');
            messageContainer.classList.add(sender, 'message');

            let identity = document.createElement('div');
            identity.classList.add('identity');
            identity.innerHTML = sender === 'user' ? '<i class="user-icon">u</i>' : '<i class="gpt user-icon">⛰</i>';

            let content = document.createElement('div');
            content.classList.add('content');

            // Add <md-block> to display the Markdown content
            let mdBlock = document.createElement('md-block');
            mdBlock.className = "markdown";
            content.appendChild(mdBlock);

            messageContainer.appendChild(identity);
            messageContainer.appendChild(content);

            document.querySelector('.conversation-view').appendChild(messageContainer);

            return mdBlock;  // Return mdBlock so we can update its content later
        }

        function updateMessageContent(mdBlock, rawText) {
            // Dynamically update the mdContent property of the mdBlock element with the raw Markdown
            mdBlock.mdContent = rawText;  // Use mdContent to dynamically update the markdown rendering
        }



function displayMessage(sender, message, images) {
    let messageContainer = document.createElement('div');
    messageContainer.classList.add(sender, 'message');

    let identity = document.createElement('div');
    identity.classList.add('identity');
    identity.innerHTML = sender === 'user' ? '<i class="user-icon">u</i>' : '<i class="gpt user-icon">⛰</i>';

    let content = document.createElement('div');
    content.classList.add('content');
    content.innerHTML = `<md-block class='markdown'>${message}</md-block>`;

    // If images are provided, display them
    if (images) {
        images.forEach(image => {
            let imgElement = document.createElement('img');
            imgElement.src = `data:image/png;base64,${image}`;  // Use the base64 image data
            imgElement.classList.add('chat-image');
            content.appendChild(imgElement);
        });
    }

    messageContainer.appendChild(identity);
    messageContainer.appendChild(content);

    document.querySelector('.conversation-view').appendChild(messageContainer);

}



function addChatToHistory(sessionId) {
    const conversationList = document.querySelector('.conversations');
    const chatItem = document.createElement('li');
    chatItem.classList.add('active');

    chatItem.innerHTML = `<button class="conversation-button" data-session-id="${sessionId}">New Chat</button>
                    <div class="fade"></div>
                    <div class="edit-buttons">
                        <button class="chat-edit" data-session-id="${sessionId}"><i class="fa fa-edit"></i></button>
                        <button class="delete-chat" data-session-id="${sessionId}"><i class="fa fa-trash"></i></button>
                    </div>
                    <input type="text" class="rename-input" data-session-id="${sessionId}" placeholder="Rename chat" style="display: none;">`;



    // Add the new chat to the top of the list
    conversationList.prepend(chatItem);

    chatItem.querySelector('.conversation-button').addEventListener('click', function() {
        loadChat(sessionId);
          });// Load the chat when clicked

    chatItem.querySelector('.chat-edit').addEventListener('click', function() {
//        const sessionId = button.getAttribute('data-session-id');
        const name = chatItem.querySelector('.conversation-button');
        const renameInput = chatItem.querySelector('.rename-input');

        renameInput.style.display = 'block'; // Show the input field

        renameInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') { // Check if Enter key is pressed
                const newChatName = renameInput.value.trim();
                if (newChatName !== '') {
                    fetch(`/rename_chat`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            session_id: sessionId,
                            new_name: newChatName
                        }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        name.innerHTML = newChatName; // Update chat name in UI
                        renameInput.style.display = 'none'; // Hide the input field
                    })
                    .catch(error => console.error('Error:', error));
                }
            }
        });
    });

chatItem.querySelector('.delete-chat').addEventListener('click', function() {
//        const sessionId = button.getAttribute('data-session-id');
        fetch(`/delete_chat`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            }),
        })
        .then(response => {
            if (response.ok) {
                chatItem.closest('li').remove(); // Remove the chat from the UI
            }
        })
        .catch(error => console.error('Error:', error));
        });
    }

function scrollToBottom() {
    const conversationView = document.querySelector('.conversation-view');
    conversationView.scrollTop = conversationView.scrollHeight;
}

function loadChat(sessionId) {
    fetch(`/chat_history?session_id=${sessionId}`)
        .then(response => response.json())
        .then(data => {
            const conversationView = document.querySelector('.conversation-view');
            conversationView.innerHTML = '';  // Clear current messages
            data.forEach(chat => {
                console.log(chat.images);
                displayMessage(chat.sender, chat.message, chat.images);  // Display each message in the chat
            });
            sessionStorage.setItem('currentSessionId', sessionId);  // Set the session ID to the one being loaded
//            document.querySelector('.conversation-view').scrollTo({ top: document.querySelector('.conversation-view').scrollHeight, behavior: 'smooth' });
            scrollToBottom()
            show_view('.conversation-view');  // Show the conversation view


        })
        .catch(error => console.error('Error:', error));
}

// Existing script.js content...

// Add event listeners for rename and delete buttons
document.querySelectorAll('.chat-edit').forEach(button => {
    button.addEventListener('click', function() {
        const sessionId = button.getAttribute('data-session-id');
        const name = document.querySelector(`.conversation-button[data-session-id="${sessionId}"]`)
        const renameInput = document.querySelector(`.rename-input[data-session-id="${sessionId}"]`);

        renameInput.style.display = 'block'; // Show the input field

        renameInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') { // Check if Enter key is pressed
                const newChatName = renameInput.value.trim();
                if (newChatName !== '') {
                    fetch(`/rename_chat`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            session_id: sessionId,
                            new_name: newChatName
                        }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        name.innerHTML = newChatName; // Update chat name in UI
                        renameInput.style.display = 'none'; // Hide the input field
                    })
                    .catch(error => console.error('Error:', error));
                }
            }
        });
    });
});

document.querySelectorAll('.delete-chat').forEach(button => {
    button.addEventListener('click', function() {
        const sessionId = button.getAttribute('data-session-id');

        fetch(`/delete_chat`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            }),
        })
        .then(response => {
            if (response.ok) {
                button.closest('li').remove(); // Remove the chat from the UI
            }
        })
        .catch(error => console.error('Error:', error));
    });
});


window.addEventListener("beforeunload", function(e) {
  sessionStorage.removeItem("currentSessionId");
});

// Handle drag and drop functionality
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileNameDisplay = document.getElementById('fileName');
        const urlInput = document.getElementById('urlInput');
        const uploadText = document.getElementById('uploadText');

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('hover');
        });

        dropZone.addEventListener('dragleave', (e) => {
            dropZone.classList.remove('hover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('hover');
            fileInput.files = e.dataTransfer.files;
            handleFileSelect(fileInput);
        });

        function handleFileSelect(input) {
            if (input.files && input.files.length > 0) {
                const file = input.files[0];
                fileNameDisplay.textContent = `Selected file: ${file.name}`;
                urlInput.disabled = true;  // Disable URL input when a file is selected
            }
        }

        function toggleFileInput() {
            if (urlInput.value.length > 0) {
                fileInput.disabled = true;  // Disable file input if a URL is provided
                fileNameDisplay.textContent = '';  // Clear the file name display
            } else {
                fileInput.disabled = false;  // Enable file input if URL is cleared
            }
        }

        function openPopup() {
            document.getElementById('popupForm').classList.add('active');
        }

        function closePopup() {
            document.getElementById('popupForm').classList.remove('active');
            fileInput.disabled = false;
            fileNameDisplay.textContent = '';
            urlInput.disabled = false;
            urlInput.value = '';
        }


//// Function to submit the form via JavaScript (AJAX)
//function submitForm() {
//    const urlInput = document.getElementById('urlInput').value.trim();
//    const fileInput = document.getElementById('fileInput').files;
//
//    const formData = new FormData();
//
//    // Check if a file is selected
//    if (fileInput.length > 0) {
//        formData.append('file', fileInput[0]);
//        // Submit the file using fetch
//        fetch('/upload_file', {
//            method: 'POST',
//            body: formData
//        })
//        .then(response => response.json())
//        .then(data => {
//            console.log('File upload response:', data);
//            alert("File Loaded Successfully!");
//            closePopup();
//        })
//        .catch(error => {
//            console.error('Error:', error);
//            alert('File Upload Failed!');
//        });
//    }
//    // Check if a URL is entered
//    else if (urlInput !== '') {
//        // Submit the URL using fetch
//        fetch('/scrape_link', {
//            method: 'POST',
//            headers: {
//                'Content-Type': 'application/json'
//            },
//            body: JSON.stringify({ url: urlInput })
//        })
//        .then(response => response.json())
//        .then(data => {
//            console.log('URL scraping response:', data);
//            alert('URL Scrapped Successfully! Please wait for a while for full website scrape');
//            closePopup();
//        })
//        .catch(error => {
//            console.error('Error:', error);
//            alert('URL Scraping Failed');
//        });
//    } else {
//        alert('Please select a file or enter a URL.');
//    }
//}


// Function to show the custom alert box with a message
function showAlert(message, type = 'error') {
    const alertBox = document.getElementById('customAlert');
    const alertMessage = document.getElementById('alertMessage');

    alertMessage.textContent = message;

    if (type === 'success') {
        alertBox.classList.add('success');
    } else {
        alertBox.classList.remove('success');
    }

    alertBox.style.display = 'block';

    // Hide the alert after 3 seconds
    setTimeout(() => {
        alertBox.style.display = 'none';
    }, 10000);
}

// Function to manually close the alert box
function closeAlert() {
    const alertBox = document.getElementById('customAlert');
    alertBox.style.display = 'none';
}

// Modify submitForm() to use the custom alert
function submitForm() {
    const urlInput = document.getElementById('urlInput').value.trim();
    const fileInput = document.getElementById('fileInput').files;
    let currentSessionId = sessionStorage.getItem('currentSessionId');
    const formData = new FormData();

    if (!currentSessionId) {
        // Create a new session if none exists
        fetch('/create_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            currentSessionId = data.session_id;
            sessionStorage.setItem('currentSessionId', currentSessionId);  // Store the new session ID
            addChatToHistory(currentSessionId);  // Add the new chat to the history
            const logo = document.querySelector('.logo');
            logo.style.display = "none";

        })
        .catch(error => console.error('Error:', error));
    }

    // Check if a file is selected
    if (fileInput.length > 0) {
        formData.append('file', fileInput[0]);
        // Submit the file using fetch
        fetch('/upload_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            sendMessage(currentSessionId, data.content, fileInput[0].name, true);
            console.log('File upload response:', data);
            showAlert('File Loaded Successfully!', 'success');
            closePopup();
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('File upload failed');
            closePopup();
        });
    }
    // Check if a URL is entered
    else if (urlInput !== '') {
        // Submit the URL using fetch
        fetch('/scrape_link', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: urlInput })
        })
        .then(response => response.json())
        .then(data => {
            sendMessage(currentSessionId, data.content, urlInput, true);
            console.log('URL scraping response:', data);
            showAlert('URL Scrapped Successfully! Please wait for a while for full website scrape', 'success');
            closePopup();
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('URL scraping failed');
            closePopup();
        });
    } else {
        showAlert('Please select a file or enter a URL.');
    }
}



function logout() {
    // Clear UID cookie
    document.cookie = 'uid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    // Clear Username cookie
    document.cookie = 'username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    // Reload the page
    window.location.reload();
}

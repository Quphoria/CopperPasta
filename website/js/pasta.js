
const debug = false;
const api_url = "/api";
// const api_url = "http://localhost:8080";
const refreshInterval = 10000; // 10 second refresh interval

var post_data = {};
var last_post_id = 0;
var refreshTimer = undefined;

var uuid = "";
var scrapbook_id = "";
var last_scrapbook = undefined;

$(function() {
    $("#content").bind("paste", handlePaste);
    $("#previewModalImagePreviewData").click(openImageInNewTab);
    $("#previewModal").on('keypress', previewModalKeypress);
    $("#modalPostButton").click(previewModalPost);
    $("#deleteScrapbook").click(deleteScrapbookConfirm);
    $("#deleteScrapbookForReal").click(deleteScrapbook);
    $("#welcomeModal").modal("show");
    $("#joinForm").submit(joinFormSubmit);
    $("#newScrapbook").click(() => { openScrapbook(); });
    $("#lastScrapbook").click(() => {
        if (last_scrapbook) {
            openScrapbook(last_scrapbook);
        }
    });
    $("#copyScrapbookName").click(() => {
        if (scrapbook_id) {
            navigator.clipboard.writeText(scrapbook_id);
            showNotification("Copied.");
        }
    });
    $("#scrapbookNameInput").change(() => {
        $("#scrapbookNameInput").val($("#scrapbookNameInput").val().toLowerCase());
    });
    doAuth();
    console.log("Loaded!");
});

function handlePaste(event) {
    if (!(uuid && scrapbook_id)) {
        return;
    }
    event.preventDefault();
    // Paste debug
    if (debug) {
        console.log("Paste Event");
        console.log(event.originalEvent.clipboardData);
        console.log("Files");
        for (var i = 0; i < event.originalEvent.clipboardData.files.length; i++) {
            console.log(event.originalEvent.clipboardData.files[i]);
        }
        console.log("Items");
        for (var i = 0; i < event.originalEvent.clipboardData.items.length; i++) {
            console.log(event.originalEvent.clipboardData.items[i]);
        }
        console.log("End");
    }

    if (event.originalEvent.clipboardData.files.length > 1) {
        showErrorModal("Error", "Multiple Files Pasted");
        return;
    } else if (event.originalEvent.clipboardData.files.length == 0) {
        if (event.originalEvent.clipboardData.items.length > 0) {
            var found_valid_paste = false;
            for (item of event.originalEvent.clipboardData.items) {
                if (item.kind == "string" && item.type == "text/plain") {
                    item.getAsString(handleTextPaste);
                    found_valid_paste = true;
                    break;
                }
            }
            if (!found_valid_paste) {
                showErrorModal("Error", "Unknown Paste");
            }
        } else {
            showErrorModal("Error", "Nothing Pasted");
        }
        return;
    }
    const file = event.originalEvent.clipboardData.files[0];
    var item = event.originalEvent.clipboardData.items[0]
    switch (file.type) {
        case "image/png":
        case "image/jpeg":
        case "image/gif":
            reader = new FileReader();
            reader.addEventListener("load", function () {
                // convert image file to base64 string
                handleImagePaste(reader.result);
            }, false);
            reader.readAsDataURL(file);
            break;
        case "text/plain":
            reader = new FileReader();
            reader.addEventListener("load", function () {
                // convert text file to text string
                handleTextPaste(reader.result);
            }, false);
            reader.readAsText(file);
            break;
        default:
            showErrorModal("Error", "Unknown file type: " + file.type);
            return;
    }
}

function handleTextPaste(text) {
    // text = text.replace(/\r?\n/g,'<br>');
    if (text == "") {
        showErrorModal("Error", "Nothing Pasted");
        return;
    }
    post_data = {
        type: "text",
        data: text
    };
    showPreviewModal("Preview", "Post Text?", "text", text);
}

function handleImagePaste(image) {
    post_data = {
        type: "image",
        data: image
    };
    showPreviewModal("Preview", "Post Image?", "image", image);
}

function showPreviewModal(title, body, type, data) {
    hideModals();
    $("#previewModalTextPreview").toggle(type=="text");
    $("#previewModalImagePreview").toggle(type=="image");
    $("#previewModalTextPreviewData").html("No Data");
    $("#previewModalImagePreviewData").attr("src","images/missing.svg");
    switch (type) {
        case "text":
            $("#previewModalTextPreviewData").text(data);
            break;
        case "image":
            $("#previewModalImagePreviewData").attr("src",data);
            break;
    }
    $('#previewModalTitle').html(title);
    $('#previewModalBody').text(body); // No XSS plz
    $('#previewModal').modal('show');
}

function previewModalKeypress (event) {
    var keycode = (event.keyCode ? event.keyCode : event.which);
    if(keycode == '13'){
        $('#modalPostButton').click();   
    }
}

function showErrorModal(title, body, deleteModal = false) {
    hideModals();
    $('#errorModalTitle').html(title);
    $('#errorModalBody').text(body); // No XSS plz
    // Select which buttons to show
    $('.error-modal-btn').toggle(!deleteModal);
    $('.delete-modal-btn').toggle(deleteModal);
    $('#errorModal').modal('show');
}

function hideModals() {
    $('#errorModal').modal('hide');
    $('#previewModal').modal('hide');
}

function createPost(data, info) {
    switch (info.type) {
        case "text":
            createTextPost(data, info);
            break;
        case "image":
            createImagePost(data, info);
            break;
        case "Error":
            createErrorPost(data, info);
            break;
        default:
            console.log("Unknown post type: " + info.type);
            break;
    }
}

function createTextPost(text, info) {
    var newPost = $($("#textPost").html());
    newPost.attr("data-id", info.id.toString());
    var text_elem = newPost.children('.card-body');
    text_elem.text(text);
    newPost.children('.card-header').append(createCardHeader(info));
    newPost.find(".copy-icon").click((event) => {
        const text = $(event.target).closest(".text-post").find(".card-body").text();
        navigator.clipboard.writeText(text);
        showNotification("Copied.");
    });
    newPost.prependTo("#posts-area");
}

function createImagePost(image, info) {
    var newPost = $($("#imagePost").html());
    newPost.attr("data-id", info.id.toString());
    var image_elem = newPost.children('.card-body');
    image_elem.attr("src", image);
    newPost.children('.card-header').append(createCardHeader(info));
    newPost.find(".copy-icon").click((event) => {
        const img = $(event.target).closest(".image-post").find(".post-image").attr("src");
        fetch(img).then(res => res.blob())
        .then(blob => {
            var item = {};
            if (blob.type == "image/png") {
                item[blob.type] = blob;
                navigator.clipboard.write([new ClipboardItem(item)]);
                showNotification("Copied.");
            } else {
                showNotification("Only text and png images can be copied with the button.", true)
            }
        });
    });
    newPost.prependTo("#posts-area");
}

function createErrorPost(text, info) {
    var newPost = $($("#textPost").html());
    newPost.attr("data-id", info.id.toString());
    var text_elem = newPost.children('.card-body');
    text_elem.text(text);
    text_elem.removeClass("text-light");
    text_elem.addClass("text-danger");
    var postHeader = $('<h5 class="text-warning mb-0">Warning</h5>');
    newPost.children('.card-header').append(postHeader);
    newPost.prependTo("#posts-area");
}

function createCardHeader(info) {
    var newPostInfo = $($("#postHeader").html());
    switch (info.type) {
        case "text":
            newPostInfo.find('.post-type').html('<i class="ri-file-text-line"></i>');
            break;
        case "image":
            newPostInfo.find('.post-type').html('<i class="ri-image-line"></i>');
            break;
    }
    newPostInfo.find('.post-client').text(info.client);
    var date = new Date(info.timestamp);
    var datestring = date.toLocaleTimeString([],
        {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute:'2-digit'
        });
    newPostInfo.find('.post-time').text(datestring);
    return newPostInfo;
}

function openImageInNewTab(event) {
    // Disgusting code to open the image in a new tab
    let w = window.open('about:blank');
    let image = new Image();
    image.src = event.target.src;
    image.style = "margin: auto;";
    setTimeout(function(){
    w.document.write(image.outerHTML);
    w.document.body.style = "display: flex; justify-content: center; align-items: center; margin: 0px; width: 100%; height: 100%;";
    w.document.body.style.backgroundColor = "#0e0e0e";
    }, 0);
}

function deleteScrapbookConfirm() {
    showErrorModal("Delete Scrapbook", "Are you sure you want to delete this scrapbook?", deleteModal=true);
}

function doAuth(auth_pass="") {
    params = {};
    if (auth_pass) {
        params.auth = auth_pass
    }

    $.ajax({url: api_url + "/auth",
        type: "GET",
        data: params,
        cache: false,
        crossDomain: true,
        xhrFields: {
            withCredentials: true
        },
        success: () => {
            fetchUUID();
    }}).fail(() => {
        auth_pass = prompt("Auth Plz");
        if (auth_pass) {
            doAuth(auth_pass);
        }
    });
}

function fetchUUID() {
    $.ajax(api_url + "/uuid", {
        type: "GET",
        cache: false,
        crossDomain: true,
        dataType: "json",
        xhrFields: {
            withCredentials: true
        },
        success: (data) => {
            if (data && data.uuid) {
                uuid = data.uuid;
                enableWelcomeForm();
            }
        }
    }).fail(() => {
        showErrorModal("Error", "Failed to get UUID");
    });
}

function enableWelcomeForm() {
    $("#loadingOverlay").hide();
    $("#newScrapbook").prop("disabled", false);
    $("#openScrapbook").prop("disabled", false);
    $("#scrapbookNameInput").focus();
    loadLastScrapbookCookie();
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("s")) {
        $("#scrapbookNameInput").val(urlParams.get("s"));
        $("#openScrapbook").click();
    }
}

function joinFormSubmit(event) {
    event.preventDefault();
    var code = $(event.target).children("[name='scrapbook']").val();

    openScrapbook(code);
}

function loadLastScrapbookCookie() {
    last_scrapbook = getCookie("last_scrapbook");
    if (last_scrapbook) {
        $("#lastScrapbook").prop("disabled", false);
        $("#lastScrapbook").show();
    }
}

function openScrapbook(code="") {
    data = {};
    if (code) {
        data.scrapbook = code;
    }

    $.ajax(api_url + "/scrapbook", {
        type: "POST",
        cache: false,
        crossDomain: true,
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify(data), 
        xhrFields: {
            withCredentials: true
        },
        success: (data) => {
            if (data && data.scrapbook) {
                scrapbook_id = data.scrapbook;
                $("#scrapbookName").text(scrapbook_id);
                setCookie("last_scrapbook", scrapbook_id, 1); // Only last 1 day
                $("#welcomeModal").modal("hide");
                refreshPosts();
                refreshTimer = setInterval(refreshPosts, refreshInterval);
            }
        }
    }).fail((error) => {
        if (error.status == 404) {
            showErrorModal("Error", "Scrapbook not found");
        } else {
            showErrorModal("Error", "Failed to load scrapbook");
        }
    });
}

var refreshing_pastes = false;

function refreshPosts(deletionForce=false) {
    if (refreshing_pastes) { return; }
    if ($('#errorModal').is(':visible') && !deletionForce) {
        return; // Don't refresh while error modal open
    }
    data = {
        start_id: last_post_id,
        scrapbook: scrapbook_id
    };
    refreshing_pastes = true;
    $.ajax(api_url + "/pastes", {
        type: "POST",
        cache: false,
        crossDomain: true,
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify(data), 
        xhrFields: {
            withCredentials: true
        },
        success: (data) => {
            if (data) {
                try {
                    var createdPosts = 0;
                    if (Array.isArray(data)) {
                        for (paste of data) {
                            if (!pasteExists(paste[0])) {
                                createPost(paste[2], {
                                    type: paste[1],
                                    id: paste[0],
                                    client: paste[3],
                                    timestamp: paste[4]
                                });
                                createdPosts++;
                                if (paste[0] > last_post_id) {
                                    last_post_id = paste[0];
                                }
                            }
                        }
                    } else if (data.error == "deleted") {
                        createPost("The Scrapbook has been deleted, if you refresh the page all the content below will be permanently deleted", {
                            type: "Error",
                            id: last_post_id + 1
                        });
                        stopRefresh();
                        if (getCookie("last_scrapbook") == scrapbook_id) {
                            eraseCookie("last_scrapbook"); // Remove cookie since it has been deleted
                        }
                        scrapbook_id = ""; // Prevent further pastes
                        $("#deleteScrapbook").prop("disabled", true);
                    } else {
                        showErrorModal("Error", "Failed to refresh pastes");
                    }
                    if (createdPosts) {
                        $("#posts-scroll-wrapper").animate({scrollTop: 0}, 1000);
                        if (createdPosts >= 5) { // Load more posts since server only sends 5 at a time
                            refreshing_pastes = false;
                            refreshPosts();
                        }
                    }
                } catch (e) {
                    showErrorModal("Error", "Failed to refresh pastes");
                    throw e;
                }
            }
        }, error: () => {
            showErrorModal("Error", "Failed to refresh pastes");
        }, complete: () => { refreshing_pastes = false; }, // after success or error
    });
}

function pasteExists(id) {
    return $("#posts-area").find(`[data-id="${id}"]`).length > 0;
}

function previewModalPost() {
    var type = post_data.type;
    var data = post_data.data;
    post_data = {};
    if (type == undefined || data == undefined) {
        console.log("Unable to post empty data");
        return;
    }

    data = {
        "scrapbook": scrapbook_id,
        "type": type,
        "data": data
    };

    $.ajax(api_url + "/paste", {
        type: "PUT",
        cache: false,
        crossDomain: true,
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify(data), 
        xhrFields: {
            withCredentials: true
        },
        success: () => {
            refreshPosts();
        }
    }).fail(() => {
        showErrorModal("Error", "Failed to send paste");
    });
}

function deleteScrapbook() {
    if (!scrapbook_id) {
        return;
    }

    $.ajax(api_url + "/scrapbook", {
        type: "DELETE",
        cache: false,
        crossDomain: true,
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify({"scrapbook": scrapbook_id}), 
        xhrFields: {
            withCredentials: true
        },
        success: () => {
            refreshPosts(true);
        }
    }).fail(() => {
        showErrorModal("Error", "Failed to delete scrapbook");
    });
}

var notification_id = 0;

function showNotification(notification, error=false) {
    var current_id = ++notification_id;
    $("#notificationOverlay").hide();
    $("#notificationBadge").text(notification);
    $("#notificationBadge").toggleClass("badge-info", !error);
    $("#notificationBadge").toggleClass("badge-warning", error);
    $("#notificationOverlay").stop(true, true).fadeIn(300, () => {
        if (notification_id == current_id) {
            setTimeout(() => {
                if (notification_id == current_id) {
                    $("#notificationOverlay").fadeOut(2000);
                }
            }, 100);
        }
    });
} 

function stopRefresh() {
    clearInterval(refreshTimer);
}

function setCookie(key, value, expiry) {
    var expires = new Date();
    expires.setTime(expires.getTime() + (expiry * 24 * 60 * 60 * 1000));
    document.cookie = key + '=' + value + ';expires=' + expires.toUTCString();
}

function getCookie(key) {
    var keyValue = document.cookie.match('(^|;) ?' + key + '=([^;]*)(;|$)');
    return keyValue ? keyValue[2] : undefined;
}

function eraseCookie(key) {
    var keyValue = getCookie(key);
    setCookie(key, keyValue, '-1');
}
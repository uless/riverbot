$(document).ready(function () {
  $('.toast').toast('hide');
  $('.waterdrop1').popover('hide');
  var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
  var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl)
  });
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  });
  // Function to display a user message in the chat interface
  function displayUserMessage(userQuery) {
    const chatHistory = document.getElementById('chatbot-prompt');
    const userMessage = document.createElement('div');
    userMessage.classList.add('card', 'user-message');
    userMessage.innerHTML = `
        <div class="card-body chatbot-question">
          <div class="col-xs-12 col-sm-12 col-md-2 col-lg-2 col-xl-1 col-2">
            <span class="fa-stack fa-1x">
              <i class="fa fa-circle fa-stack-2x user-icon-background"></i>
              <i class="fa fa-user fa-stack-1x text-light"></i>
            </span>
          </div>
          <div class="col-xs-12 col-sm-12 col-md-10 col-lg-10 col-xl-11 col-10 welcome-message-body">
            ${userQuery}
          </div>
        </div>
      `;
    chatHistory.appendChild(userMessage);
  }

  function showReactions(message) {
    $(message).find('.reactions').show();
  }

  function hideReactions(message) {
    $(message).find('.reactions').hide();
  }

  function completeRequest() {
    $('.toast').toast('show');
  }

  function submitReaction($clickedReaction) {
    const reactionValue = $clickedReaction.data('reaction');
    console.log("Sending reaction: " + reactionValue);
    const messageID = $clickedReaction.attr("data-messageid");

    if (reactionValue == 0)
      $("#modal-" + messageID).find(".modal-header >i").removeClass("bi bi-hand-thumbs-up").addClass("bi bi-hand-thumbs-down");
    // Send a POST request with the selected reaction and message
    fetch('/submit_rating_api', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          'reaction': reactionValue,
          'message_id': messageID,
        }),
      })
      .then(response => response.text())
      .then(message => {
        console.log(message); // Handle the response as needed
        $("button.comment[data-messageid=" + messageID + "]").attr("data-reaction", reactionValue);

      });
  }

  function submitComment($clickedReaction) {
    const reactionValue = $clickedReaction.data('reaction');

    const messageID = $clickedReaction.parent().parent().find("button.comment").attr("data-messageid");
    var commentInput = $clickedReaction.parent().parent().find('#userComment-' + messageID).val();
    var feedbackMsg = `
    <div class="card-footer">
    <div class="row">
      <div class="col-1"></div>
      <div class="col-11">
        <span class="feedback-${messageID}" data-messageid="${messageID}">Thanks for your feedback</span>     
      </div>
      </div>
    </div>`;
    console.log("Sending comment: " + commentInput + " for " + messageID);
    // Send a POST request with the selected reaction and message
    fetch('/submit_rating_api', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          'userComment': commentInput,
          'message_id': messageID,
        }),
      })
      .then(response => response.text())
      .then(message => {
        console.log(message); // Handle the response as needed
        //Remove one of the reactions

        if (reactionValue == "1") {
          //means thumbs-up
          //remove thumbs-down
          $("span.reaction[data-reaction='0'][data-messageid=" + messageID + "]").remove();

          //Remove click event from thumbs up
          $("span.reaction[data-reaction='1'][data-messageid=" + messageID + "]").removeAttr("data-bs-toggle");
          $("span.reaction[data-reaction='1'][data-messageid=" + messageID + "]").removeAttr("data-bs-target");

          //Replace the icon to fill
          //$("span.reaction[data-reaction='1'][data-messageid="+messageID+"] > i").removeClass("bi-hand-thumbs-up").addClass("bi-hand-thumbs-up-fill");

          $("span.reaction[data-reaction='1'][data-messageid=" + messageID + "] > i").addClass("reaction-feedback");

          $("span.reaction[data-reaction='1'][data-messageid=" + messageID + "]").removeClass("reaction");

        } else {
          //remove thumbs-up
          $("span.reaction[data-reaction='1'][data-messageid=" + messageID + "]").remove();

          //Remove click event from thumbs up
          $("span.reaction[data-reaction='0'][data-messageid=" + messageID + "]").removeAttr("data-bs-toggle");
          $("span.reaction[data-reaction='0'][data-messageid=" + messageID + "]").removeAttr("data-bs-target");

          //Replace the icon to fill
          //$("span.reaction[data-reaction='0'][data-messageid="+messageID+"] > i").removeClass("bi-hand-thumbs-down").addClass("bi-hand-thumbs-down-fill");
          $("span.reaction[data-reaction='0'][data-messageid=" + messageID + "] > i").addClass("reaction-feedback");

          $("span.reaction[data-reaction='0'][data-messageid=" + messageID + "]").removeClass("reaction");
        }

        //Close the modal popup
        $("#modal-" + messageID).modal('toggle');
        $(".card.data-messageid-" + messageID).append(feedbackMsg);
        scrollToBottom();

        //   $('#waterdropFeedback').popover('show');
        //   setTimeout(function () {
        //     $('#waterdropFeedback').popover('hide');
        // }, 2000);
        //completeRequest();
      });
  }
  // Function to display a bot message in the chat interface
  function displayBotMessage(botResponse, messageID) {
    const chatHistory = document.getElementById('chatbot-prompt');
    const botMessage = document.createElement('div');
    botMessage.classList.add('card', 'bot-message');
    botMessage.classList.add('card', 'data-messageid-' + messageID);
    botMessage.innerHTML = `
        <div class="card-body welcome-message pb-0" data-messageid=${messageID}>
        <div class="row">
          <div class="col-xs-12 col-sm-12 col-md-2 col-lg-2 col-xl-1 col-2">
            <img class="waterdrop1" />
          </div>
          <div class="col-xs-12 col-sm-12 col-md-10 col-lg-10 col-xl-11 col-10 bot-message-body">
            ${botResponse}
          </div>
          
          </div>
        </div>
        <div class="card-footer" style="padding:8px; border:0;">
          <div class="row">
            <div class="col-1"></div>
            <div class="col-11">
              <span class="reaction" data-toggle="tooltip" data-placement="top" title="Good response" data-bs-toggle="modal" data-messageid=${messageID} data-bs-target="#modal-${messageID}" data-reaction="1"><i class="bi bi-hand-thumbs-up fa-1x"></i></span>  
              <span class="reaction" data-toggle="tooltip" data-placement="top" title="Could be better" data-bs-toggle="modal" data-messageid=${messageID} data-bs-target="#modal-${messageID}" data-reaction="0"><i class="bi bi-hand-thumbs-down fa-1x"></i></span>
            </div>
          </div>
        </div>

        <!-- Modal -->
        <div class="modal fade" id="modal-${messageID}" tabindex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
              <i class="bi bi-hand-thumbs-up fa-1x reaction-feedback" style="width:48px;"></i><h1 class="modal-title fs-5" id="exampleModalLabel">
                &nbsp;
                Why did you choose this rating?</h1>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body">
              <textarea placeholder="Provide additional feedback" class="userComment form-control" id ="userComment-${messageID}"></textarea>
              </div>
              <div class="modal-footer">
                <button class="comment btn btn-primary btn-new-chat" data-messageid=${messageID} data-user-comment-target=".userComment">Submit</button>                
              </div>
            </div>
          </div>
        </div>
      `;
    chatHistory.appendChild(botMessage);
  }

  $(document).on('click', '.comment', function () {
    submitComment($(this));
  });

  // Function to display a loading animation message in the chat interface
  function displayLoadingAnimation() {
    $("div.loading-animation").remove();
    const chatHistory = document.getElementById('chatbot-prompt');
    const botMessage = document.createElement('div');
    botMessage.classList.add('card', 'loading-animation');
    botMessage.innerHTML = `
          <div class="card-body">
            <div class="dot-flashing"></div>
        </div>
      `;
    chatHistory.appendChild(botMessage);

    //Showing loading animation before the response
    $(".loading-animation").css("display", "flex");
  }

  function removeLoadingAnimation() {
    //Removing loading animation after the response
    $(".loading-animation").css("display", "none");
  }

  // Function to send user queries to the backend and receive responses
  function sendUserQuery(e) {
    const userQuery = document.getElementById('user_query').value;
    e.preventDefault();

    if (userQuery.trim() === '') {
      return; // Don't send empty queries
    }

    // Display the user's message in the chat
    displayUserMessage(userQuery);

    //Start of the loading animation
    displayLoadingAnimation();
    $("#user_query").prop('disabled', true);
    $("#submit-button").prop('disabled', true);

    //Scroll to bottom script
    scrollToBottom();

    // Define the URL of your Flask server
    //const apiUrl = `/chat_api`; // Replace with the actual URL if needed

    // Create a request body with the user query
    const requestBody = new FormData();
    requestBody.append('user_query', userQuery);

    // Make a POST request to the server
    // Create an EventSource to listen for events from the server
    const eventSource = new EventSource(`/chat_stream_api?user_query=${encodeURIComponent(userQuery)}`);
    var msg = "";
    var cardCount = $(".card-body[data-messageid]").length +1;
    eventSource.onmessage = (event) => {
      // Handle incoming events here
      if (event.data == 'end_of_stream_waterbot_blue') {
        displayBotMessage(msg, cardCount);

        //Removing loading animation
        removeLoadingAnimation();
        
        eventSource.close();

      } else {
        msg+=event.data;
        $(".card-body[data-messageid="+cardCount+"]").find(".bot-message-body").append(event.data);
      }
    }

    $("#user_query").prop('disabled', false);
    $("#submit-button").prop('disabled', false);

    // fetch(apiUrl, {
    //     method: 'POST',
    //     body: requestBody,
    //   })
    //   .then(response => response.json())
    //   .then(botResponse => {
    //     // Display the bot's response in the chat
    //     debugger;
    //     displayBotMessage(botResponse.resp, botResponse.msgID);
    //     //typewriter(botResponse);

    //     //Removing loading animation
    //     removeLoadingAnimation();
    //     $("#user_query").prop('disabled', false);
    //     $("#submit-button").prop('disabled', false);
    //     //Scroll to bottom function
    //     scrollToBottom();
    //   })
    //   .catch(error => {
    //     console.error('Error:', error);
    //     removeLoadingAnimation();
    //     $("#user_query").prop('disabled', false);
    //     $("#submit-button").prop('disabled', false);
    //     scrollToBottom();
    //   });

    scrollToBottom();

    // Clear the input field after sending the query
    document.getElementById('user_query').value = '';

  }

  $("#user_query").on('keyup', function (e) {
    e.preventDefault();
    if (e.key === 'Enter' || e.keyCode === 13) {
      sendUserQuery(e);
    }
  });

  $("#submit-button").on('click', function (e) {
    e.preventDefault();
    sendUserQuery(e);
  });

  $(document).on('mouseover', '.welcome-message', function () {
    showReactions($(this));
  });

  $(document).on('mouseout', '.welcome-message', function () {
    hideReactions($(this));
  });

  // Bind click event to submit the reaction for all elements with the class 'reactions'
  $(document).on('click', '.reaction', function () {
    submitReaction($(this));
    const messageID = $(this).parent().parent().find("button.comment").attr("data-messageid");
    const reactionId = $(this).attr("data-reaction");
    $("#modal-" + messageID).find("button.comment").attr("data-reaction", reactionId);
  });


  function scrollToBottom() {
    $("#chatbot-prompt").scrollTop($('#chatbot-prompt')[0].scrollHeight - $('#chatbot-prompt')[0].clientHeight);
  }

});
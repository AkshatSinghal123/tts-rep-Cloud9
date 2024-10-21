<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Text To Speech Converter</title>
    <link
      href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap"
      rel="stylesheet"
    />
    <style>
      body {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
        background-color: #e2bfd9;
        font-family: "Poppins", sans-serif;
      }

      .container {
        background-color: #001f3f;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        width: 400px;
        text-align: center;
      }

      .title {
        color: #fff;
        font-size: 2rem;
        margin-bottom: 20px;
      }

      .upload-area {
        border: 2px dashed #fff;
        color: #fff;
        padding: 40px;
        cursor: pointer;
        transition: background-color 0.3s;
        border-radius: 8px;
        margin-bottom: 20px;
      }

      .upload-area:hover {
        background-color: #e7f3ff;
        color: #001f3f;
      }

      .file-name {
        margin: 10px 0;
        color: #fff;
      }

      .language-input {
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #fff;
        width: 100%;
        margin-bottom: 20px;
        font-size: 1rem;
        color: #000;
        box-sizing: border-box;
      }

      .btn {
        background-color: #007bff;
        color: #fff;
        padding: 10px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        width: 100%;
        font-size: 1rem;
      }

      .btn:hover {
        background-color: #0056b3;
      }

      .audio-container {
        display: none;
        margin-top: 20px;
      }

      .audio-container audio {
        width: 100%;
      }

      .error {
        color: red;
        margin-top: 20px;
      }

      .hidden {
        display: none;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1 class="title">Text to Speech Converter</h1>

      <div class="upload-area" id="uploadArea">
        Click to upload or drag and drop your CSV file
      </div>
      <input type="file" id="fileInput" hidden />
      <p id="fileName" class="file-name"></p>

      <input
        type="text"
        id="languageInput"
        class="language-input"
        placeholder="Enter Locale (e.g., en-US, pt-BR)"
      />

      <button id="convertBtn" class="btn">Convert to Audio</button>

      <!-- Container for English audio -->
      <div id="englishAudioContainer" class="audio-container">
        <h3>English Audio:</h3>
        <audio id="englishAudioPlayer" controls></audio>
        <br />
        <a id="englishDownloadBtn" class="btn" download>Download English Audio</a>
      </div>

      <!-- Container for Language-specific audio -->
      <div id="languageAudioContainer" class="audio-container">
        <h3>Language-Specific Audio:</h3>
        <audio id="languageAudioPlayer" controls></audio>
        <br />
        <a id="languageDownloadBtn" class="btn" download>Download Language Audio</a>
      </div>

      <div id="error" class="error"></div>
    </div>

    <script>
      const uploadArea = document.getElementById("uploadArea");
      const fileInput = document.getElementById("fileInput");
      const fileNameDisplay = document.getElementById("fileName");
      const languageInput = document.getElementById("languageInput");
      const convertBtn = document.getElementById("convertBtn");
      const englishAudioContainer = document.getElementById("englishAudioContainer");
      const englishAudioPlayer = document.getElementById("englishAudioPlayer");
      const englishDownloadBtn = document.getElementById("englishDownloadBtn");
      const languageAudioContainer = document.getElementById("languageAudioContainer");
      const languageAudioPlayer = document.getElementById("languageAudioPlayer");
      const languageDownloadBtn = document.getElementById("languageDownloadBtn");
      const errorDiv = document.getElementById("error");

      // Click to open file selector
      uploadArea.addEventListener("click", () => fileInput.click());

      // File drag-and-drop functionality
      uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadArea.style.backgroundColor = "#e7f3ff";
      });

      uploadArea.addEventListener("dragleave", () => {
        uploadArea.style.backgroundColor = "";
      });

      uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadArea.style.backgroundColor = "";
        const file = e.dataTransfer.files[0];
        if (file) {
          fileInput.files = e.dataTransfer.files;
          fileNameDisplay.textContent = `Selected file: ${file.name}`;
        }
      });

      // Display selected file name when file is chosen
      fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (file) {
          fileNameDisplay.textContent = `Selected file: ${file.name}`;
        }
      });

      // Convert button click event
      convertBtn.addEventListener("click", async () => {
        const file = fileInput.files[0];
        const language = languageInput.value.trim();

        if (!file) {
          alert("Please upload a file.");
          return;
        }
        if (!language) {
          alert("Please enter a language.");
          return;
        }

        const formData = new FormData();
        formData.append("file", file);
        formData.append("source", language);

        try {
          // Change this URL to your FastAPI endpoint
          const response = await fetch("https://8c6e4a2d086143619af72776e05bbc3a.vfs.cloud9.ap-south-1.amazonaws.com/upload-csv/", {
            method: "POST",
            body: formData,
          });

          const result = await response.json();

          if (result.english_audio_link && result.language_audio_link) {
            // Set audio player and download button for English audio
            englishAudioPlayer.src = result.english_audio_link;
            englishDownloadBtn.href = result.english_audio_link;
            englishDownloadBtn.download = "english_audio.wav";
            englishAudioContainer.style.display = "block";

            // Set audio player and download button for language-specific audio
            languageAudioPlayer.src = result.language_audio_link;
            languageDownloadBtn.href = result.language_audio_link;
            languageDownloadBtn.download = "language_audio.wav";
            languageAudioContainer.style.display = "block";

            errorDiv.textContent = ""; // Clear error
          } else if (result.error) {
            errorDiv.textContent = `Error: ${result.error}`;
          }
        } catch (error) {
          errorDiv.textContent = "An error occurred. Please try again.";
        }
      });
    </script>
  </body>
</html>

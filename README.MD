### **Version 1: Initial UI Integration with Combined English and Portuguese Audio Output**

In this initial version, I developed a user-friendly interface (UI) that allows users to upload a CSV file containing transcriptions. Upon uploading, the application generates a combined audio output featuring both English and Portuguese versions of the transcription. Additionally, a single SSML file is created, containing the transcriptions for both languages. The focus of this version was to streamline the process of combining both languages into a single audio output, making it convenient for users who need bilingual audio files.

---

### **Version 2: Independent Audio Generation for English and Portuguese**

Building upon the first version, this iteration provides users with more flexibility by allowing them to generate two separate audio files—one for English and one for Portuguese. Each language now has its own independent CSV file, and the UI allows users to generate and display these audio files separately. This approach gives users more control over the audio outputs, allowing them to choose individual languages for different purposes.

---

### **Version 3: Locale-Based Audio and SSML Generation via API**

In this version, a key client requirement was addressed by implementing locale-based audio generation via an API. Users can now upload a CSV file and specify a locale (e.g., `en-US` for English or `pt-BR` for Portuguese) via a POST request. The application generates both an audio file and an SSML file for the language specified by the locale. By default, English audio and SSML files are generated alongside the locale-specific files, ensuring that English is always included. This provides greater flexibility for generating files in multiple languages.

---

### **Version 4: Dockerized Application Running on Port 8080**

This version focuses on simplifying deployment and scalability by Dockerizing the application. The application is packaged into a Docker container and runs on port 8080, ensuring that it can be easily deployed in any containerized environment. This version enhances the consistency of the application across different environments and allows for efficient scaling as needed.

---

### **Version 5: Deployment with IAM Role, AWS ECS Fargate, and Language Detection for Transcriptions**

In the latest version, I integrated AWS ECS with Fargate and deployed the backend web application using an Application Load Balancer (ALB) to enable secure and scalable access. The application now leverages an IAM role for secure access to AWS services like Secrets Manager, removing the need for hardcoded credentials. 

Additionally, I enhanced the code to detect and validate transcriptions. The application now supports CSVs containing a `PT--Transcription` column and auto-detects the language under this column. If the transcription under `PT--Transcription` is not in Portuguese (e.g., if another language is mistakenly used), the system automatically detects the error and notifies the user. This ensures data accuracy and provides immediate feedback when the expected language does not match the transcription.

This version offers improved deployment, security, and advanced language detection capabilities, making the application more robust and scalable for enterprise use.# tts-cloud9-repo

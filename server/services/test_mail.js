const nodemailer = require("nodemailer");
const path = require("path");
const fs = require("fs");
const dotenv = require("dotenv");

const envPath = path.resolve(__dirname, "../../.env");
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
} else {
  dotenv.config();
}

console.log("Using Email:", process.env.EMAIL);

// Create transporter with logging enabled
const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 465,
  secure: true,
  debug: true,
  logger: true,
  auth: {
    user: process.env.EMAIL,
    pass: process.env.PASS,
  },
  tls: {
    rejectUnauthorized: false,
  }
});

const mailOptions = {
  from: process.env.EMAIL,
  to: process.env.EMAIL,
  subject: "Test Diagnostic",
  text: "This is a diagnostic mail from DistillNews."
};

transporter.sendMail(mailOptions)
  .then(() => {
    console.log("SUCCESS");
    process.exit(0);
  })
  .catch((err) => {
    console.error("FAILURE:", err);
    process.exit(1);
  });

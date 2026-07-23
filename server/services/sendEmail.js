const nodemailer = require("nodemailer");
const generateNewsEmailHTML = require("./generateEmail.js");
const fs = require("fs");
const path = require("path");

// Load environment variables
require("dotenv").config();

// Load HTML template and replace placeholders
async function loadTemplate(filePath, replacements) {
  const resolvedPath = path.resolve(__dirname, filePath);

  try {
    let template = await fs.promises.readFile(resolvedPath, "utf-8");
    for (const key in replacements) {
      template = template.replace(
        new RegExp(`{{${key}}}`, "g"),
        replacements[key]
      );
    }
    return template;
  } catch (error) {
    console.error("Error reading email template:", error);
    throw error;
  }
}
console.log("process.env.EMAIL:", process.env.EMAIL);
console.log("process.env.PASS:", process.env.PASS);
// Configure Nodemailer
const transporter = nodemailer.createTransport({
  service: "gmail",
  host: "smtp.gmail.com",
  port: 465,
  secure: true,
  auth: {
    user: process.env.EMAIL,
    pass: process.env.PASS,
  },
  tls: {
    rejectUnauthorized: false,
  },
});
// const generateArticlesHTML = (articles) => {
//   return articles
//     .map((article) => {
//       return `
//         <div style="margin-bottom: 30px; padding: 10px; border-bottom: 1px solid #ccc;">
//           <h2 style="margin: 0 0 10px;">${article.title}</h2>
//           ${
//             article.image
//               ? `<img src="${article.image}" alt="" style="max-width:100%; height:auto; margin-bottom:10px;" />`
//               : ""
//           }
//           <p>${article.description || ""}</p>
//           <a href="${article.url}" target="_blank">Read more</a>
//         </div>
//       `;
//     })
//     .join("\n");
// };



const sendOTPEmail = async (recipientEmail, otp) => {
console.log("process.env.EMAIL:", process.env.EMAIL);
console.log("process.env.PASS:", process.env.PASS);

  try {
    const htmlContent = `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #333; text-align: center;">Verify Your Email</h2>
        <p>Hello,</p>
        <p>Your one-time password (OTP) for DistillNews is:</p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 5px; text-align: center; margin: 30px 0; color: #007bff;">
          ${otp}
        </div>
        <p>This OTP is valid for 5 minutes. Please do not share this code with anyone.</p>
        <p>Best regards,<br/>The DistillNews Team</p>
      </div>
    `;

    const mailOptions = {
      from: process.env.EMAIL,
      to: recipientEmail,
      subject: `🔑 Your OTP Verification Code`,
      html: htmlContent,
    };

    await transporter.sendMail(mailOptions);
    console.log("OTP sent to", recipientEmail);
  } catch (error) {
    console.error("Error sending OTP email:", error);
    throw error;
  }
};

const sendNewsLetterEmail = async (recipientEmail) => {
  try {
    var data = null;
    try {
      const res = await fetch("http://localhost:8000/feeds")
      data = (await res.json()).feeds;
    } catch (e) {
      console.log("Error sending email");
      return;
    }
    if (data === null) {
      console.log("Error sending email");
      return;
    }
    const htmlContent = generateNewsEmailHTML(data);

    const mailOptions = {
      from: process.env.EMAIL,
      to: recipientEmail,
      subject: `📰 Your Daily Newsletter`,
      html: htmlContent,
    };

    await transporter.sendMail(mailOptions);
    console.log("Newsletter sent to", recipientEmail);
  } catch (error) {
    console.error("Error sending newsletter email:", error);
  }
};

const mode = process.argv[2]; // "otp" or email recipient
const recipient = process.argv[3];
const otpValue = process.argv[4];

if (mode === "otp") {
  if (!recipient || !otpValue) {
    console.error("Usage: node sendEmail.js otp <email> <otp>");
    process.exit(1);
  }
  sendOTPEmail(recipient, otpValue)
    .then(() => process.exit(0))
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
} else {
  // Fallback mode for backward compatibility
  const emailToSend = mode || "nishant040305@gmail.com";
  sendNewsLetterEmail(emailToSend)
    .then(() => process.exit(0))
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}

module.exports = {
  sendNewsLetterEmail,
  sendOTPEmail,
};

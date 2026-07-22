const nodemailer = require("nodemailer");
const generateNewsEmailHTML = require("./generateEmail.js");

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



const sendNewsLetterEmail = async (recipientEmail) => {
  try {
    var data = null;
    try {
      const res = await fetch("http://localhost:8000/feeds")
      data = (await res.json()).feeds;
    } catch (e){
      console.log("Error sending email");
      return;
    }
    if (data === null){
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

sendNewsLetterEmail("nishant040305@gmail.com")
.then(res => console.log(res))
.catch(err => console.log(err))

module.exports = {
  sendNewsLetterEmail,
};

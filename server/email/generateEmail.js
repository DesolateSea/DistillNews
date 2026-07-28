const WEBSITE_URL = process.env.WEBSITE_URL;
function generateNewsEmailHTML(newsItems) {
  const grouped = {};

  // Group news by category
  for (const item of newsItems) {
    const category = item.category || "Others";
    if (!grouped[category]) grouped[category] = [];
    grouped[category].push(item);
  }

  const currentDate = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const styles = `
      body {
        font-family: Arial, sans-serif;
        background: #f4f4f4;
        color: #333;
        padding: 20px;
        max-width: 800px;
        margin: auto;
      }
      .category {
        background: #333;
        color: #fff;
        padding: 10px;
        margin-top: 30px;
        border-radius: 4px;
      }
      .article {
        background: #fff;
        padding: 15px;
        margin: 20px 0;
        border-radius: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
      }
      .headline {
        margin: 0 0 8px;
        font-size: 1.4em;
        color: #222;
      }
      .metadata {
        font-size: 0.9em;
        color: #777;
        margin-bottom: 10px;
      }
      .summary {
        font-weight: bold;
        margin-bottom: 10px;
      }
      .article-image {
        max-width: 100%;
        height: auto;
        margin-bottom: 10px;
        border-radius: 4px;
      }
      .content p {
        margin: 10px 0;
      }
      .tags {
        margin-top: 12px;
      }
      .tag {
        display: inline-block;
        background: #e0e0e0;
        padding: 5px 10px;
        margin: 2px;
        border-radius: 3px;
        font-size: 0.8em;
        color: #555;
      }
    `;
  const today = new Date();
  const options = {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  };
  const dateToday = today.toLocaleDateString("en-US", options);
  let html = `<html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Daily News Digest</title>
            <style>
                body {
                    font-family: Georgia, 'Times New Roman', Times, serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f7f1;
                    color: #333;
                }
                .header {
                    text-align: center;
                    border-bottom: 3px double #000;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }
                .masthead {
                    font-size: 42px;
                    font-weight: bold;
                    letter-spacing: 1px;
                    margin: 0;
                }
                .date {
                    font-style: italic;
                    margin: 5px 0 15px;
                }
                .category {
                    border-bottom: 1px solid #333;
                    margin: 30px 0 15px;
                    padding-bottom: 5px;
                    font-size: 22px;
                    font-weight: bold;
                    text-transform: uppercase;
                }
                .article {
                    margin-bottom: 25px;
                    overflow: hidden;
                }
                .headline {
                    font-size: 20px;
                    font-weight: bold;
                    margin: 0 0 10px;
                }
                .metadata {
                    font-size: 12px;
                    color: #555;
                    margin-bottom: 10px;
                }
                .summary {
                    font-style: italic;
                    font-size: 15px;
                    margin-bottom: 10px;
                }
                .content {
                    line-height: 1.5;
                }
                .article-image {
                    float: right;
                    max-width: 200px;
                    margin-left: 15px;
                    margin-bottom: 10px;
                }
                .tags {
                    font-size: 12px;
                    color: #666;
                    margin-top: 10px;
                }
                .tag {
                    background: #eee;
                    padding: 2px 5px;
                    border-radius: 3px;
                    margin-right: 5px;
                }
                blockquote {
                    border-left: 3px solid #ccc;
                    margin-left: 0;
                    padding-left: 15px;
                    font-style: italic;
                }
                .footer {
                    text-align: center;
                    border-top: 1px solid #333;
                    padding-top: 15px;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #555;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1 class="masthead">THE DAILY CHRONICLE</h1>
                 <div class="date">${dateToday}</div>
                 </div>`;

  for (const [category, articles] of Object.entries(grouped)) {
    html += `<h2 class="category">${category}</h2>`;
    for (const article of articles) {
      html += `
        <div class="article">
          <h3 class="headline">
            <a href="${process.env.CLIENT}/${
        article.id
      }" style="color: black; text-decoration: none;">
              ${article.title || "Untitled"}
            </a>
          </h3>
          <div class="metadata">
            Published: ${
              article.publication_date?.slice(0, 10) || "N/A"
            } | Location: ${article.location || "Unknown"}
          </div>
          <div class="summary">
            ${article.summary || "No summary available."}
          </div>
        </div>
      `;
    }
  }

  html += `
    <a href='${WEBSITE_URL}'>View more news</a>
    </body>
    </html>
    `;

  return html;
}

module.exports = generateNewsEmailHTML;

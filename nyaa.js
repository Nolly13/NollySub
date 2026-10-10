const NYAA_BASE_URL = 'https://nyaa.si';

const CATEGORIES = Object.freeze({
  ALL: '0_0',
  ANIME: {
    ALL: '1_0',
    MUSIC_VIDEO: '1_1',
    ENGLISH_TRANSLATED: '1_2',
    NON_ENGLISH_TRANSLATED: '1_3',
    RAW: '1_4',
  },
  AUDIO: {
    ALL: '2_0',
    LOSSLESS: '2_1',
    LOSSY: '2_2',
  },
  LITERATURE: {
    ALL: '3_0',
    ENGLISH_TRANSLATED: '3_1',
    NON_ENGLISH_TRANSLATED: '3_2',
    RAW: '3_3',
  },
  LIVE_ACTION: {
    ALL: '4_0',
    ENGLISH_TRANSLATED: '4_1',
    IDOL_PROMOTIONAL_VIDEO: '4_2',
    NON_ENGLISH_TRANSLATED: '4_3',
    RAW: '4_4',
  },
  PICTURES: {
    ALL: '5_0',
    GRAPHICS: '5_1',
    PHOTOS: '5_2',
  },
  SOFTWARE: {
    ALL: '6_0',
    APPLICATIONS: '6_1',
    GAMES: '6_2',
  },
});

const FILTER_TYPES = Object.freeze({
  NO_FILTER: 0,
  NO_REMAKES: 1,
  TRUSTED_ONLY: 2,
});

const SORT_FIELDS = Object.freeze({
  ID: 'id',
  SIZE: 'size',
  COMMENTS: 'comments',
  SEEDERS: 'seeders',
  LEECHERS: 'leechers',
  DOWNLOADS: 'downloads',
});

const SORT_ORDERS = Object.freeze({
  ASCENDING: 'asc',
  DESCENDING: 'desc',
});

const HTML_ENTITY_MAP = Object.freeze({
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#39;': "'",
  '&apos;': "'",
});

const DEFAULT_SEARCH_OPTIONS = Object.freeze({
  query: '',
  category: CATEGORIES.ALL,
  filter: FILTER_TYPES.NO_FILTER,
  page: 1,
  sortBy: null,
  sortOrder: SORT_ORDERS.DESCENDING,
  baseUrl: NYAA_BASE_URL,
});

function decodeHtmlEntities(rawText) {
  if (!rawText || typeof rawText !== 'string') {
    return '';
  }

  return rawText.replace(/&(?:amp|lt|gt|quot|#39|apos);/g, (matchedEntity) => {
    return HTML_ENTITY_MAP[matchedEntity] || matchedEntity;
  });
}

function stripHtmlTags(rawHtml) {
  if (!rawHtml || typeof rawHtml !== 'string') {
    return '';
  }

  return decodeHtmlEntities(rawHtml.replace(/<[^>]*>/g, '').trim());
}

function extractAttributeValue(elementHtml, attributeName) {
  const attributeRegex = new RegExp(`${attributeName}=["']([^"']*)["']`, 'i');
  const matchedResult = elementHtml.match(attributeRegex);
  return matchedResult ? decodeHtmlEntities(matchedResult[1]) : null;
}

function parseCategoryData(categoryCellHtml) {
  const linkMatch = categoryCellHtml.match(/<a\s+[^>]*href=["']\/\?c=([0-9_]+)["'][^>]*title=["']([^"']*)["']/i);
  if (!linkMatch) {
    return { code: CATEGORIES.ALL, name: 'Unknown' };
  }

  return {
    code: linkMatch[1],
    name: decodeHtmlEntities(linkMatch[2]),
  };
}

function parseTitleAndComments(titleCellHtml) {
  const commentMatch = titleCellHtml.match(/<a\s+[^>]*class=["'][^"']*comments[^"']*["'][^>]*>[\s\S]*?(\d+)<\/a>/i);
  const commentCount = commentMatch ? parseInt(commentMatch[1], 10) : 0;

  const viewLinkMatch = titleCellHtml.match(/<a\s+[^>]*href=["']\/view\/(\d+)["'][^>]*title=["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>/i);
  if (!viewLinkMatch) {
    return {
      torrentId: null,
      title: '',
      commentCount,
    };
  }

  const torrentId = viewLinkMatch[1];
  const title = decodeHtmlEntities(viewLinkMatch[2] || stripHtmlTags(viewLinkMatch[3]));

  return {
    torrentId,
    title,
    commentCount,
  };
}

function parseDownloadLinks(linkCellHtml, baseUrl) {
  const torrentFileMatch = linkCellHtml.match(/href=["'](\/download\/\d+\.torrent)["']/i);
  const magnetMatch = linkCellHtml.match(/href=["'](magnet:\?[^"']+)["']/i);

  const torrentRelativePath = torrentFileMatch ? torrentFileMatch[1] : null;
  const torrentUrl = torrentRelativePath ? `${baseUrl}${torrentRelativePath}` : null;
  const magnetLink = magnetMatch ? decodeHtmlEntities(magnetMatch[1]) : null;

  return {
    torrentUrl,
    magnetLink,
  };
}

function extractInfoHashFromMagnet(magnetUri) {
  if (!magnetUri) {
    return null;
  }

  const hashMatch = magnetUri.match(/xt=urn:btih:([a-zA-Z0-9]+)/i);
  return hashMatch ? hashMatch[1].toLowerCase() : null;
}

function parseNumericCell(cellHtml) {
  const textContent = stripHtmlTags(cellHtml);
  const parsedNumber = parseInt(textContent, 10);
  return Number.isNaN(parsedNumber) ? 0 : parsedNumber;
}

function parseDateCell(dateCellHtml) {
  const timestampString = extractAttributeValue(dateCellHtml, 'data-timestamp');
  const timestamp = timestampString ? parseInt(timestampString, 10) : null;
  const formattedDate = stripHtmlTags(dateCellHtml);

  return {
    timestamp,
    dateString: formattedDate,
  };
}

function parseRowClassification(rowTagHtml) {
  const classAttribute = extractAttributeValue(rowTagHtml, 'class') || '';
  const classTokens = classAttribute.split(/\s+/);

  return {
    isTrusted: classTokens.includes('success'),
    isRemake: classTokens.includes('danger'),
    isBatch: classTokens.includes('info'),
  };
}

function parseTableRow(rowHtml, baseUrl) {
  const cells = rowHtml.match(/<td[\s\S]*?<\/td>/gi);
  if (!cells || cells.length < 8) {
    return null;
  }

  const openingRowTag = rowHtml.match(/<tr[^>]*>/i)?.[0] || '';
  const classification = parseRowClassification(openingRowTag);
  const categoryData = parseCategoryData(cells[0]);
  const titleData = parseTitleAndComments(cells[1]);
  const linkData = parseDownloadLinks(cells[2], baseUrl);
  const dateData = parseDateCell(cells[4]);

  return {
    id: titleData.torrentId,
    title: titleData.title,
    category: categoryData,
    torrentUrl: linkData.torrentUrl,
    magnetLink: linkData.magnetLink,
    infoHash: extractInfoHashFromMagnet(linkData.magnetLink),
    viewUrl: titleData.torrentId ? `${baseUrl}/view/${titleData.torrentId}` : null,
    fileSize: stripHtmlTags(cells[3]),
    timestamp: dateData.timestamp,
    uploadDate: dateData.dateString,
    seeders: parseNumericCell(cells[5]),
    leechers: parseNumericCell(cells[6]),
    downloads: parseNumericCell(cells[7]),
    commentsCount: titleData.commentCount,
    isTrusted: classification.isTrusted,
    isRemake: classification.isRemake,
    isBatch: classification.isBatch,
  };
}

function parsePaginationData(htmlContent) {
  const paginationMatch = htmlContent.match(/<ul\s+class=["']pagination["']>([\s\S]*?)<\/ul>/i);
  if (!paginationMatch) {
    return {
      currentPage: 1,
      hasNextPage: false,
      totalPages: 1,
    };
  }

  const paginationHtml = decodeHtmlEntities(paginationMatch[1]);
  const activePageMatch = paginationHtml.match(/<li\s+class=["']active["']>\s*<a[^>]*>(\d+)/i);
  const currentPage = activePageMatch ? parseInt(activePageMatch[1], 10) : 1;

  const pageNumberMatches = [...paginationHtml.matchAll(/[?&]p=(\d+)/g)];
  const pageNumbers = pageNumberMatches.map((match) => parseInt(match[1], 10));
  const maxPageFound = pageNumbers.length > 0 ? Math.max(...pageNumbers) : currentPage;
  const totalPages = Math.max(currentPage, maxPageFound);
  const hasNextPage = paginationHtml.includes('rel="next"') || totalPages > currentPage;

  return {
    currentPage,
    hasNextPage,
    totalPages,
  };
}

function parseNyaaHtml(htmlContent, baseUrl = NYAA_BASE_URL) {
  if (!htmlContent || typeof htmlContent !== 'string') {
    return {
      results: [],
      pagination: {
        currentPage: 1,
        hasNextPage: false,
        totalPages: 1,
      },
    };
  }

  const tbodyMatch = htmlContent.match(/<tbody>([\s\S]*?)<\/tbody>/i);
  if (!tbodyMatch) {
    return {
      results: [],
      pagination: parsePaginationData(htmlContent),
    };
  }

  const rowMatches = tbodyMatch[1].match(/<tr[\s\S]*?<\/tr>/gi) || [];
  const results = [];

  for (let index = 0; index < rowMatches.length; index += 1) {
    const parsedItem = parseTableRow(rowMatches[index], baseUrl);
    if (parsedItem) {
      results.push(parsedItem);
    }
  }

  return {
    results,
    pagination: parsePaginationData(htmlContent),
  };
}

function buildSearchUrl(searchOptions = {}) {
  const mergedOptions = { ...DEFAULT_SEARCH_OPTIONS, ...searchOptions };
  const targetUrl = new URL(mergedOptions.baseUrl);

  targetUrl.searchParams.set('f', String(mergedOptions.filter));
  targetUrl.searchParams.set('c', String(mergedOptions.category));
  targetUrl.searchParams.set('q', String(mergedOptions.query));

  if (mergedOptions.page > 1) {
    targetUrl.searchParams.set('p', String(mergedOptions.page));
  }

  if (mergedOptions.sortBy) {
    targetUrl.searchParams.set('s', String(mergedOptions.sortBy));
    targetUrl.searchParams.set('o', String(mergedOptions.sortOrder));
  }

  return targetUrl.toString();
}

async function searchNyaa(searchOptions = {}) {
  const requestUrl = buildSearchUrl(searchOptions);
  const baseUrl = searchOptions.baseUrl || NYAA_BASE_URL;

  const response = await fetch(requestUrl, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  });

  if (!response.ok) {
    throw new Error(`Nyaa request failed with status code ${response.status}: ${response.statusText}`);
  }

  const htmlResponse = await response.text();
  const parsedData = parseNyaaHtml(htmlResponse, baseUrl);

  return {
    query: searchOptions.query || '',
    category: searchOptions.category || CATEGORIES.ALL,
    filter: searchOptions.filter ?? FILTER_TYPES.NO_FILTER,
    requestUrl,
    ...parsedData,
  };
}

const NyaaApi = {
  CATEGORIES,
  FILTER_TYPES,
  SORT_FIELDS,
  SORT_ORDERS,
  buildSearchUrl,
  parseNyaaHtml,
  searchNyaa,
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = NyaaApi;
  module.exports.default = NyaaApi;
  module.exports.CATEGORIES = CATEGORIES;
  module.exports.FILTER_TYPES = FILTER_TYPES;
  module.exports.SORT_FIELDS = SORT_FIELDS;
  module.exports.SORT_ORDERS = SORT_ORDERS;
  module.exports.buildSearchUrl = buildSearchUrl;
  module.exports.parseNyaaHtml = parseNyaaHtml;
  module.exports.searchNyaa = searchNyaa;
}

export default NyaaApi;
export {
  CATEGORIES,
  FILTER_TYPES,
  SORT_FIELDS,
  SORT_ORDERS,
  buildSearchUrl,
  parseNyaaHtml,
  searchNyaa,
};

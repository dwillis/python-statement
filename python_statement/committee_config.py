"""
Configuration for congressional committee press release scrapers.

This is a separate collection from member scrapers (SCRAPER_CONFIG in
config.py). The canonical list of committees is committees-current.yaml from
https://github.com/unitedstates/congress-legislators; every entry here is
keyed to a committee's ``thomas_id`` from that file.

Entries use the same methods and selector keys as SCRAPER_CONFIG, plus two
required metadata keys:

    thomas_id  Committee id from committees-current.yaml (e.g. 'HSAG', 'SSFI')
    side       'majority', 'minority', or 'full' (one shared newsroom)

Keys must be ``<thomas_id lowercase>_<side>``, e.g. ``hsag_majority``.
Results from these scrapers carry ``committee`` (thomas_id) and ``side``.
"""

import re

from .config import SCRAPER_CONFIG, validate_config


COMMITTEE_CONFIG = {
    # House
    'hlig_majority': {'thomas_id': 'HLIG', 'side': 'majority', 'method': 'generic', 'url_base': 'https://intelligence.house.gov/category/press-releases/', 'container': '.news-wrapper a.item', 'title_sel': '.title', 'date_sel': '.date-bar', 'date_fmt': ['%B %d %Y'], 'pagination': 'page/{page}/'},
    'hlig_minority': {'thomas_id': 'HLIG', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-intelligence.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '&Page={page}'},
    'hsag_majority': {'thomas_id': 'HSAG', 'side': 'majority', 'method': 'generic', 'url_base': 'https://agriculture.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&page={page}'},
    'hsag_minority': {'thomas_id': 'HSAG', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-agriculture.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&page={page}'},
    'hsap_majority': {'thomas_id': 'HSAP', 'side': 'majority', 'method': 'generic', 'url_base': 'https://appropriations.house.gov/news/press-releases', 'container': '.media-body', 'title_sel': '.font-weight-bold a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsap_minority': {'thomas_id': 'HSAP', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-appropriations.house.gov/news/press-releases', 'container': '.media-body', 'title_sel': '.font-weight-bold a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsas_majority': {'thomas_id': 'HSAS', 'side': 'majority', 'method': 'generic', 'url_base': 'https://armedservices.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&page={page}'},
    'hsas_minority': {'thomas_id': 'HSAS', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-armedservices.house.gov/press-releases', 'container': 'tr', 'title_sel': 'td a', 'date_sel': 'time', 'date_fmt': ['%m/%d/%y', '%B %d, %Y'], 'skip_first': 1, 'pagination': '?PageNum_rs={page}'},
    'hsba_majority': {'thomas_id': 'HSBA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://financialservices.house.gov/news/documentquery.aspx?DocumentTypeID=2092', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&page={page}'},
    'hsba_minority': {'thomas_id': 'HSBA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-financialservices.house.gov/newsroom/documentquery.aspx?DocumentTypeID=2636', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&page={page}'},
    'hsbu_majority': {'thomas_id': 'HSBU', 'side': 'majority', 'method': 'generic', 'url_base': 'https://budget.house.gov/news/press-releases/table', 'container': 'tr', 'title_sel': 'td a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'hsbu_minority': {'thomas_id': 'HSBU', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-budget.house.gov/news/press-releases', 'container': '.media-body', 'title_sel': '.font-weight-bold a', 'date_regex': '((?:January|February|March|April|May|June|July|August|September|October|November|December) \\d{1,2}, \\d{4})', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsed_majority': {'thomas_id': 'HSED', 'side': 'majority', 'method': 'generic', 'url_base': 'https://edworkforce.house.gov/news/documentquery.aspx?DocumentTypeID=1823', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'hsed_minority': {'thomas_id': 'HSED', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-edworkforce.house.gov/media/press-releases/table', 'container': 'tr', 'title_sel': 'td a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'hsfa_majority': {'thomas_id': 'HSFA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://foreignaffairs.house.gov/news/press-releases', 'container': '.media-body', 'title_sel': '.font-weight-bold a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsfa_minority': {'thomas_id': 'HSFA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-foreignaffairs.house.gov/category/press-releases/', 'container': 'article', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/?et_blog'},
    'hsgo_majority': {'thomas_id': 'HSGO', 'side': 'majority', 'method': 'generic', 'url_base': 'https://oversight.house.gov/release/', 'container': 'div.post', 'title_sel': '.title', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'hsgo_minority': {'thomas_id': 'HSGO', 'side': 'minority', 'method': 'generic', 'url_base': 'https://oversightdemocrats.house.gov/news/press-releases', 'container': 'tr', 'title_sel': 'td a', 'date_sel': 'time', 'date_fmt': ['%m/%d/%y', '%B %d, %Y'], 'skip_first': 1, 'pagination': '?PageNum_rs={page}'},
    'hsha_majority': {'thomas_id': 'HSHA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://cha.house.gov/media/press-releases', 'container': '.media-body', 'title_sel': '.font-weight-bold a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsha_minority': {'thomas_id': 'HSHA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-cha.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hshm_majority': {'thomas_id': 'HSHM', 'side': 'majority', 'method': 'generic', 'url_base': 'https://homeland.house.gov/press/', 'container': 'a.news-post', 'title_sel': '.title', 'date_sel': '.date', 'date_fmt': ['%m/%d/%y'], 'pagination': 'page/{page}/'},
    'hshm_minority': {'thomas_id': 'HSHM', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-homeland.house.gov/news/press-releases/table/', 'container': 'tr', 'title_sel': 'td a', 'date_sel': 'time', 'date_fmt': ['%m/%d/%y', '%B %d, %Y'], 'skip_first': 1, 'pagination': '?PageNum_rs={page}'},
    # Next.js site: HTML holds only the latest 9 posts; no pagination available.
    'hsif_majority': {'thomas_id': 'HSIF', 'side': 'majority', 'method': 'generic', 'url_base': 'https://energycommerce.house.gov/news/press-release', 'container': 'article', 'title_sel': 'h3', 'link_sel': 'a[href^="/posts/"]', 'date_sel': '.utility-font.label > div', 'date_fmt': ['%b %d, %Y'], 'pagination': ''},
    'hsif_minority': {'thomas_id': 'HSIF', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-energycommerce.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': 'a', 'date_sel': '.evo-card-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsii_majority': {'thomas_id': 'HSII', 'side': 'majority', 'method': 'generic', 'url_base': 'https://naturalresources.house.gov/news/documentquery.aspx?DocumentTypeID=1634', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '&Page={page}'},
    'hsii_minority': {'thomas_id': 'HSII', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-naturalresources.house.gov/media/press-releases/table', 'container': 'tr:has(td.date)', 'title_sel': 'td a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'hsju_majority': {'thomas_id': 'HSJU', 'side': 'majority', 'method': 'generic', 'url_base': 'https://judiciary.house.gov/media/press-releases', 'container': '.views-row:has(.media-body)', 'title_sel': 'a', 'date_sel': '.row .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsju_minority': {'thomas_id': 'HSJU', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-judiciary.house.gov/media-center/press-releases', 'container': '.media-body', 'title_sel': 'a', 'date_sel': '.row .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hspw_majority': {'thomas_id': 'HSPW', 'side': 'majority', 'method': 'generic', 'url_base': 'https://transportation.house.gov/news/documentquery.aspx?DocumentTypeID=2545', 'container': 'ul.UnorderedNewsList li', 'title_sel': 'a.middleheadline', 'date_regex': 'on (\\w+ \\d{1,2}, \\d{4})', 'date_fmt': ['%B %d, %Y'], 'pagination': '&Page={page}'},
    'hspw_minority': {'thomas_id': 'HSPW', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-transportation.house.gov/news/press-releases/table', 'container': 'tr:has(td.date)', 'title_sel': 'td a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'hsru_majority': {'thomas_id': 'HSRU', 'side': 'majority', 'method': 'generic', 'url_base': 'https://rules.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%dT%H:%M:%S%z'], 'pagination': '?page={page}', 'page_offset': -1},
    'hsru_minority': {'thomas_id': 'HSRU', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-rules.house.gov/media/press-releases', 'container': '.media-body', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%dT%H:%M:%SZ'], 'pagination': '?page={page}', 'page_offset': -1},
    'hssm_majority': {'thomas_id': 'HSSM', 'side': 'majority', 'method': 'generic', 'url_base': 'https://smallbusiness.house.gov/news/documentquery.aspx?DocumentTypeID=1684', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '&Page={page}'},
    'hssm_minority': {'thomas_id': 'HSSM', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-smallbusiness.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '&Page={page}'},
    'hsso_full': {'thomas_id': 'HSSO', 'side': 'full', 'method': 'generic', 'url_base': 'https://ethics.house.gov/press-releases/', 'container': '.grid-section__list-item', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    # Listing dates lack a year; dates come from each item page (1 extra request per item).
    'hssy_majority': {'thomas_id': 'HSSY', 'side': 'majority', 'method': 'generic', 'url_base': 'https://science.house.gov/press-releases', 'container': '.recordList .media-digest', 'title_sel': '.post-media-digest-title', 'link_sel': 'a.media-digest-body-link', 'detail_date_sel': 'h3 span.date', 'detail_date_fmt': ['%B%d,%Y', '%B %d, %Y'], 'pagination': '?page={page}'},
    'hssy_minority': {'thomas_id': 'HSSY', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-science.house.gov/news/press-releases/table', 'container': 'tr:has(td.date)', 'title_sel': 'td a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'hsvr_majority': {'thomas_id': 'HSVR', 'side': 'majority', 'method': 'generic', 'url_base': 'https://veterans.house.gov/news/documentquery.aspx?DocumentTypeID=2613', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '&Page={page}'},
    'hsvr_minority': {'thomas_id': 'HSVR', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-veterans.house.gov/news/press-releases/table', 'container': 'tr', 'title_sel': 'td a', 'date_sel': 'time', 'date_fmt': ['%m/%d/%y', '%B %d, %Y'], 'skip_first': 1, 'pagination': '?PageNum_rs={page}'},
    'hswm_majority': {'thomas_id': 'HSWM', 'side': 'majority', 'method': 'generic', 'url_base': 'https://waysandmeans.house.gov/category/press-releases/', 'container': '.news-item', 'title_sel': '.title a', 'date_sel': '.date-bar', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'hswm_minority': {'thomas_id': 'HSWM', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-waysandmeans.house.gov/media-center/press-releases', 'container': '.media-body', 'title_sel': 'a', 'date_sel': ':scope > div:nth-of-type(2)', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hszs_majority': {'thomas_id': 'HSZS', 'side': 'majority', 'method': 'generic', 'url_base': 'https://selectcommitteeontheccp.house.gov/media/press-releases', 'container': '.views-row:has(.media-body)', 'title_sel': 'a', 'date_sel': '.row .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'hszs_minority': {'thomas_id': 'HSZS', 'side': 'minority', 'method': 'generic', 'url_base': 'https://democrats-selectcommitteeontheccp.house.gov/media/press-releases', 'container': '.views-row:has(.media-body)', 'title_sel': '.media-body a', 'date_sel': '.row .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},

    # Senate
    'scnc_full': {'thomas_id': 'SCNC', 'side': 'full', 'method': 'generic', 'url_base': 'https://www.drugcaucus.senate.gov/media-center/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h4', 'link_sel': 'a.jet-engine-listing-overlay-link', 'date_sel': 'time', 'date_fmt': ['%m.%d.%y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    # Entire archive is one page; no pagination.
    'slet_full': {'thomas_id': 'SLET', 'side': 'full', 'method': 'generic', 'url_base': 'https://www.ethics.senate.gov/public/index.cfm/pressreleases', 'container': 'table.recordList tr', 'title_sel': 'a', 'date_sel': 'td.recordListDate', 'date_fmt': ['%m/%d/%y'], 'pagination': ''},
    'slia_majority': {'thomas_id': 'SLIA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.indian.senate.gov/newsroom/republican-news/', 'container': '.jet-listing-grid__item', 'title_sel': 'a', 'date_sel': '.jet-listing-dynamic-field__content', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'slia_minority': {'thomas_id': 'SLIA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.indian.senate.gov/newsroom/democratic-news/', 'container': '.jet-listing-grid__item', 'title_sel': 'a', 'date_sel': '.jet-listing-dynamic-field__content', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    # Rarely updated (newest release 2022).
    'slin_full': {'thomas_id': 'SLIN', 'side': 'full', 'method': 'generic', 'url_base': 'https://www.intelligence.senate.gov/reports-publications/press-releases/', 'container': 'article.et_pb_post:not(.et_pb_has_overlay)', 'title_sel': '.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/?et_blog'},
    'spag_majority': {'thomas_id': 'SPAG', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.aging.senate.gov/press-room/majority', 'container': 'li.PageList__item', 'title_sel': 'a.ArticleBlock__link', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'spag_minority': {'thomas_id': 'SPAG', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.aging.senate.gov/press-room/minority', 'container': 'li.PageList__item', 'title_sel': 'a.ArticleBlock__link', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'ssaf_majority': {'thomas_id': 'SSAF', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.agriculture.senate.gov/newsroom/majority-news', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssaf_minority': {'thomas_id': 'SSAF', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.agriculture.senate.gov/newsroom/minority-news', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssap_majority': {'thomas_id': 'SSAP', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.appropriations.senate.gov/news/majority/table/', 'container': '#browser_table tr', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'ssap_minority': {'thomas_id': 'SSAP', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.appropriations.senate.gov/news/minority/table/', 'container': '#browser_table tr', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'ssas_full': {'thomas_id': 'SSAS', 'side': 'full', 'method': 'generic', 'url_base': 'https://www.armed-services.senate.gov/press-releases', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssbk_majority': {'thomas_id': 'SSBK', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.banking.senate.gov/newsroom/majority-press-releases', 'container': 'table.table tr', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'ssbk_minority': {'thomas_id': 'SSBK', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.banking.senate.gov/newsroom/minority-press-releases', 'container': 'table.table tr', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?PageNum_rs={page}'},
    'ssbu_majority': {'thomas_id': 'SSBU', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.budget.senate.gov/chairman/newsroom/press/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'time', 'date_fmt': ['%m.%d.%y'], 'pagination': '{page}/'},
    'ssbu_minority': {'thomas_id': 'SSBU', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.budget.senate.gov/ranking-member/newsroom/press/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'time', 'date_fmt': ['%m.%d.%y'], 'pagination': '{page}/'},
    'sscm_majority': {'thomas_id': 'SSCM', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.commerce.senate.gov/press/republican-news/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'span.elementor-heading-title', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},
    'sscm_minority': {'thomas_id': 'SSCM', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.commerce.senate.gov/press/democratic-news/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'span.elementor-heading-title', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},
    'sseg_majority': {'thomas_id': 'SSEG', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.energy.senate.gov/republican/republican-press/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'span.elementor-heading-title', 'date_fmt': ['%m.%d.%y'], 'pagination': '{page}/'},
    'sseg_minority': {'thomas_id': 'SSEG', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.energy.senate.gov/democratic/democratic-press/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'span.elementor-heading-title', 'date_fmt': ['%m.%d.%y'], 'pagination': '{page}/'},
    'ssev_majority': {'thomas_id': 'SSEV', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.epw.senate.gov/press/majority-press/', 'container': '.e-loop-item', 'title_sel': 'h3 a', 'date_sel': '.HearingItem__date p', 'date_sel_join': True, 'date_fmt': ['%b %d %Y'], 'pagination': '{page}/'},
    'ssev_minority': {'thomas_id': 'SSEV', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.epw.senate.gov/press/minority-press/', 'container': '.e-loop-item', 'title_sel': 'h3 a', 'date_sel': '.HearingItem__date p', 'date_sel_join': True, 'date_fmt': ['%b %d %Y'], 'pagination': '{page}/'},
    'ssfi_majority': {'thomas_id': 'SSFI', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.finance.senate.gov/newsroom/chairmans-news/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'time', 'date_fmt': ['%m/%d/%y'], 'pagination': '{page}/'},
    'ssfi_minority': {'thomas_id': 'SSFI', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.finance.senate.gov/newsroom/ranking-members-news/', 'container': '.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'time', 'date_fmt': ['%m/%d/%y'], 'pagination': '{page}/'},
    'ssfr_majority': {'thomas_id': 'SSFR', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.foreign.senate.gov/press/chair', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssfr_minority': {'thomas_id': 'SSFR', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.foreign.senate.gov/press/ranking', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    # Listing dates lack a year; dates come from each item page (1 extra request per item).
    'ssga_majority': {'thomas_id': 'SSGA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.hsgac.senate.gov/media/majority-news/', 'container': '.jet-listing-grid__item', 'title_sel': 'h5', 'link_sel': 'a.jet-engine-listing-overlay-link', 'detail_date_sel': 'time', 'detail_date_fmt': ['%A, %B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'ssga_minority': {'thomas_id': 'SSGA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.hsgac.senate.gov/media/minority-news/', 'container': '.jet-listing-grid__item', 'title_sel': 'h5', 'link_sel': 'a.jet-engine-listing-overlay-link', 'detail_date_sel': 'time', 'detail_date_fmt': ['%A, %B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'sshr_majority': {'thomas_id': 'SSHR', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.help.senate.gov/chair/newsroom/press', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?pagenum_rs={page}'},
    'sshr_minority': {'thomas_id': 'SSHR', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.help.senate.gov/ranking/newsroom/press', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?pagenum_rs={page}'},
    'ssju_majority': {'thomas_id': 'SSJU', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.judiciary.senate.gov/press/majority', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssju_minority': {'thomas_id': 'SSJU', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.judiciary.senate.gov/press/minority', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssra_majority': {'thomas_id': 'SSRA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.rules.senate.gov/news/majority-news', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'ssra_minority': {'thomas_id': 'SSRA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.rules.senate.gov/news/minority-news', 'container': 'li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'sssb_majority': {'thomas_id': 'SSSB', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.sbc.senate.gov/public/index.cfm/republicanpressreleases', 'container': 'table.recordList tr', 'title_sel': 'a', 'date_sel': 'td.recordListDate', 'date_fmt': ['%m/%d/%y'], 'pagination': '?page={page}'},
    'sssb_minority': {'thomas_id': 'SSSB', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.sbc.senate.gov/public/index.cfm/democraticpressreleases', 'container': 'table.recordList tr', 'title_sel': 'a', 'date_sel': 'td.recordListDate', 'date_fmt': ['%m/%d/%y'], 'pagination': '?page={page}'},
    'ssva_majority': {'thomas_id': 'SSVA', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.veterans.senate.gov/majority-news', 'container': 'div.element-inner', 'title_sel': 'a.media-list-body-link', 'date_sel': '.post-media-list-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}'},
    'ssva_minority': {'thomas_id': 'SSVA', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.veterans.senate.gov/minority-news', 'container': 'div.element-inner', 'title_sel': 'a.media-list-body-link', 'date_sel': '.post-media-list-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}'},

    # Joint
    'jcse_full': {'thomas_id': 'JCSE', 'side': 'full', 'method': 'generic', 'url_base': 'https://www.csce.gov/press-releases', 'container': '.views-row', 'title_sel': '.views-field-title a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%dT%H:%M:%SZ'], 'pagination': '?page={page}', 'page_offset': -1},
    # Republican newsroom mixes economic updates with releases.
    'jsec_majority': {'thomas_id': 'JSEC', 'side': 'majority', 'method': 'generic', 'url_base': 'https://www.jec.senate.gov/public/index.cfm/republicans/newsroom', 'container': 'div.media-list > a', 'title_sel': 'h3', 'date_sel': 'span.post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}'},
    'jsec_minority': {'thomas_id': 'JSEC', 'side': 'minority', 'method': 'generic', 'url_base': 'https://www.jec.senate.gov/public/index.cfm/democrats/press-releases', 'container': 'article', 'title_sel': 'h1.title a', 'date_sel': 'span.date span', 'date_sel_join': True, 'date_fmt': ['%b %d %Y'], 'pagination': '?page={page}'},
}

# Committees in committees-current.yaml that are deliberately not scraped,
# keyed by thomas_id, with the reason.
COMMITTEE_SKIP = {
    'HSQJ': 'Select subcommittee of the 118th Congress; no website listed',
    'JSLC': 'No press releases; cha.house.gov page lists only rules and membership',
    'JSPR': 'No press releases; cha.house.gov page lists only rules and membership',
    'JSTX': 'jct.gov blocks automated requests (403); publishes technical reports, not press releases',
}

COMMITTEE_META_KEYS = frozenset({'thomas_id', 'side'})
VALID_SIDES = {'majority', 'minority', 'full'}
THOMAS_ID_RE = re.compile(r'^[A-Z]{4}$')


def validate_committee_config(configs=None, member_config=None):
    """Validate committee config entries.

    Runs the standard member checks (method, url_base, selectors, unknown
    keys) and the committee-specific ones: thomas_id and side present and
    well-formed, key equals ``<thomas_id>_<side>``, no name shared with a
    member scraper.
    """
    if configs is None:
        configs = COMMITTEE_CONFIG
    if member_config is None:
        member_config = SCRAPER_CONFIG

    validate_config(configs, extra_keys=COMMITTEE_META_KEYS)

    for name, config in configs.items():
        thomas_id = config.get('thomas_id')
        side = config.get('side')
        if not thomas_id:
            raise ValueError(f"Committee scraper '{name}': missing required key 'thomas_id'")
        if not THOMAS_ID_RE.match(thomas_id):
            raise ValueError(
                f"Committee scraper '{name}': thomas_id '{thomas_id}' must be "
                f"four uppercase letters (e.g. 'HSAG')"
            )
        if not side:
            raise ValueError(f"Committee scraper '{name}': missing required key 'side'")
        if side not in VALID_SIDES:
            raise ValueError(
                f"Committee scraper '{name}': side '{side}' must be one of {sorted(VALID_SIDES)}"
            )
        expected = f"{thomas_id.lower()}_{side}"
        if name != expected:
            raise ValueError(
                f"Committee scraper '{name}': key must be '{expected}' "
                f"(<thomas_id lowercase>_<side>)"
            )
        if name in member_config:
            raise ValueError(
                f"Committee scraper '{name}': name collides with a member scraper"
            )


validate_committee_config()

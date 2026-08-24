"""
Configuration for scrapers that use generic methods.
Maps scraper_method name -> {method: generic_method_name, url_base: base_url}
"""

SCRAPER_CONFIG = {
    # table_recordlist_date pattern - Senate sites with table.recordListDate
    'moran': {'method': 'table_recordlist_date', 'url_base': 'https://www.moran.senate.gov/public/index.cfm/news-releases'},
    'boozman': {'method': 'table_recordlist_date', 'url_base': 'https://www.boozman.senate.gov/public/index.cfm/press-releases'},
    'thune': {'method': 'generic', 'url_base': 'https://www.thune.senate.gov/news/press-releases/', 'container': 'a.news-item', 'title_sel': 'h3', 'date_sel': 'time', 'date_sel_join': True, 'date_fmt': ['%b %d'], 'pagination': '?e-page-b9709a3={page}'},
    'barrasso': {'method': 'generic', 'url_base': 'https://www.barrasso.senate.gov/newsroom/news-releases/', 'container': 'article.elementor-post', 'title_sel': 'h3 a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},
    'graham': {'method': 'table_recordlist_date', 'url_base': 'https://www.lgraham.senate.gov/public/index.cfm/press-releases'},
    'klobuchar': {'method': 'table_recordlist_date', 'url_base': 'https://www.klobuchar.senate.gov/public/index.cfm/news-releases'},
    'mcconnell': {'method': 'table_recordlist_date', 'url_base': 'https://www.mcconnell.senate.gov/public/index.cfm/pressreleases'},
    
    # jet_listing_elementor pattern - WordPress/Elementor sites
    'timscott': {'method': 'jet_listing_elementor', 'url_base': 'https://www.scott.senate.gov/media-center/press-releases/jsf/jet-engine:press-list'},
    'cassidy': {'method': 'generic', 'url_base': 'https://www.cassidy.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list', 'container': 'div.ArticleBlock', 'title_sel': 'h2 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%m.%d.%Y'], 'pagination': '&pagenum={page}'},
    # fetterman and tester moved to generic pattern below
    'marshall': {'method': 'generic', 'url_base': 'https://www.marshall.senate.gov/newsroom/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h4 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:list&pagenum={page}'},
    # britt moved to generic pattern below
    'toddyoung': {'method': 'generic', 'url_base': 'https://www.young.senate.gov/newsroom/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h2 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    # markkelly moved to generic pattern below
    'lujan': {'method': 'jet_listing_elementor', 'url_base': 'https://www.lujan.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list'},
    # mullin moved to generic pattern below
    'ossoff': {'method': 'jet_listing_elementor', 'url_base': 'https://www.ossoff.senate.gov/press-releases/?jsf=jet-engine:press-list'},
    
    # article_block_h2_p_date pattern - Senate sites with ArticleBlock
    'chrismurphy': {'method': 'generic', 'url_base': 'https://www.murphy.senate.gov/newsroom/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'h1 a', 'date_sel': 'span.ArticleBlock__date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'markey': {'method': 'generic', 'url_base': 'https://www.markey.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a.ArticleBlock__title__link', 'date_sel': 'p.ArticleBlock__date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'cotton': {'method': 'generic', 'url_base': 'https://www.cotton.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a.ArticleTitle__link', 'date_sel': 'p.ArticleBlock__date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'rounds': {'method': 'generic', 'url_base': 'https://www.rounds.senate.gov/newsroom/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'h2.ArticleTitle', 'link_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?PageNum_rs={page}'},
    'kaine': {'method': 'generic', 'url_base': 'https://www.kaine.senate.gov/news', 'container': 'div.ArticleBlock', 'title_sel': 'a.ArticleTitle', 'date_sel': 'p.Heading--overline', 'date_fmt': ['%B %d %Y'], 'pagination': '?PageNum_rs={page}'},
    'durbin': {'method': 'senate_drupal_newscontent', 'url_base': 'https://www.durbin.senate.gov/newsroom/press-releases'},
    'crapo': {'method': 'generic', 'url_base': 'https://www.crapo.senate.gov/media/newsreleases', 'container': 'div.ArticleBlock', 'title_sel': 'h2.ArticleTitle', 'link_sel': 'a[href]', 'date_sel': 'p.Heading--time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'hirono': {'method': 'generic', 'url_base': 'https://www.hirono.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a.ArticleTitle', 'date_sel': 'p.Heading--time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'ernst': {'method': 'generic', 'url_base': 'https://www.ernst.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'garypeters': {'method': 'generic', 'url_base': 'https://www.peters.senate.gov/newsroom/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?PageNum_rs={page}'},
    'jackreed': {'method': 'generic', 'url_base': 'https://www.reed.senate.gov/news/releases', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'heinrich': {'method': 'generic', 'url_base': 'https://www.heinrich.senate.gov/newsroom/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'h2.ArticleTitle', 'link_sel': 'a.ArticleBlock__link', 'date_sel': 'p.Heading--time', 'pagination': '?PageNum_rs={page}'},
    'aguilar': {'method': 'generic', 'url_base': 'https://aguilar.house.gov/category/congress_press_release/', 'container': 'div.item', 'title_sel': 'h2 a', 'date_sel': '.date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'bergman': {'method': 'generic', 'url_base': 'https://bergman.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'cantwell': {'method': 'generic', 'url_base': 'https://www.cantwell.senate.gov/news/press-releases', 'container': 'table tr', 'title_sel': 'td a', 'date_sel': 'td', 'date_fmt': ['%m/%d/%y'], 'pagination': '?PageNum_rs={page}'},
    'capito': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.capito.senate.gov/news/press-releases'},
    'carey': {'method': 'generic', 'url_base': 'https://carey.house.gov/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'cortezmasto': {'method': 'generic', 'url_base': 'https://www.cortezmasto.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': '.ArticleBlock__title a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': ''},
    'cruz': {'method': 'generic', 'url_base': 'https://www.cruz.senate.gov/newsroom/press-releases', 'container': 'a.ArticleBlock', 'title_sel': 'h2', 'date_sel': 'p.Heading--overline', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?PageNum_rs={page}'},
    'daines': {'method': 'generic', 'url_base': 'https://www.daines.senate.gov/news/press-releases/', 'container': 'article.elementor-post', 'title_sel': 'h3 a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'duckworth': {'method': 'senate_drupal_newscontent', 'url_base': 'https://www.duckworth.senate.gov/news/press-releases'},
    'ellzey': {'method': 'generic', 'url_base': 'https://ellzey.house.gov/', 'container': 'a.update-link', 'title_sel': 'div.post-title', 'date_sel': 'span.date', 'date_fmt': ['%B %d, %Y'], 'base_domain': 'ellzey.house.gov'},
    'gimenez': {'method': 'table_recordlist_date', 'url_base': 'https://gimenez.house.gov/press-releases'},
    'hassan': {'method': 'generic', 'url_base': 'https://www.hassan.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%b %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'coons': {'method': 'generic', 'url_base': 'https://www.coons.senate.gov/news/press-releases/', 'container': 'div.ArticleBlock', 'title_sel': 'a.elementor-button', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'hydesmith': {'method': 'generic', 'url_base': 'https://www.hydesmith.senate.gov/newsroom', 'container': '.views-row', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%dT%H:%M:%SZ']},
    'lankford': {'method': 'article_block_h2_p_date', 'url_base': 'https://www.lankford.senate.gov/news/press-releases'},
    'lofgren': {'method': 'generic', 'url_base': 'https://lofgren.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': 'a[rel="bookmark"]', 'detail_date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1, 'max_results': 10},
    'lucas': {'method': 'react', 'url_base': 'https://lucas.house.gov/press'},
    'merkley': {'method': 'generic', 'url_base': 'https://www.merkley.senate.gov/news/press-releases/', 'container': 'article.elementor-post', 'title_sel': 'h2.elementor-post__title a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'mikelee': {'method': 'generic', 'url_base': 'https://www.lee.senate.gov/press-releases', 'container': 'div.element', 'title_sel': 'h2.element-title a', 'date_sel': 'h3.element-date', 'date_fmt': ['%b %d, %Y'], 'pagination': '?page={page}'},
    'paul': {'method': 'generic', 'url_base': 'https://www.paul.senate.gov/news/', 'container': 'article.et_pb_post', 'title_sel': 'h2.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'pressley': {'method': 'generic', 'url_base': 'https://pressley.house.gov/news/', 'container': 'a.post', 'title_sel': 'p.title', 'date_sel': 'p.date', 'date_fmt': ['%b %d, %Y', '%B %d, %Y'], 'pagination': 'page/{page}/'},
    'reschenthaler': {'method': 'senate_drupal_newscontent', 'url_base': 'https://reschenthaler.house.gov/media/press-releases'},
    'risch': {'method': 'generic', 'url_base': 'https://www.risch.senate.gov/public/index.cfm/press-releases', 'container': 'div.e-con.e-parent', 'title_sel': 'h2 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'ronjohnson': {'method': 'generic', 'url_base': 'https://www.ronjohnson.senate.gov/category/press-releases/', 'container': 'article.et_pb_post', 'title_sel': '.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'schatz': {'method': 'generic', 'url_base': 'https://www.schatz.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'a.Heading--h3', 'date_sel': 'p.Heading--overline', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?PageNum_rs={page}'},
    'shaheen': {'method': 'generic', 'url_base': 'https://www.shaheen.senate.gov/news/press', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': 'time.Heading--time', 'date_fmt': ['%m.%d.%Y'], 'pagination': '?PageNum_rs={page}'},
    'whitehouse': {'method': 'generic', 'url_base': 'https://www.whitehouse.senate.gov/news/release', 'container': 'div.ArticleBlock', 'title_sel': '.ArticleBlock__title a', 'date_sel': 'h3.elementor-heading-title', 'date_fmt': ['%B %d, %Y'], 'pagination': ''},
    'wyden': {'method': 'senate_drupal_newscontent', 'url_base': 'https://www.wyden.senate.gov/news/press-releases'},

    # element_post_media pattern - Senate sites with .element class
    'tillis': {'method': 'element_post_media', 'url_base': 'https://www.tillis.senate.gov/press-releases'},
    'wicker': {'method': 'generic', 'url_base': 'https://www.wicker.senate.gov/category/press-releases/', 'container': 'article', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'blackburn': {'method': 'element_post_media', 'url_base': 'https://www.blackburn.senate.gov/news/cc8c80c1-d564-4bbb-93a4-f1d772346ae0'},

    # table_time pattern - House sites with table and <time> elements
    'buchanan': {'method': 'generic', 'url_base': 'https://buchanan.house.gov/media/', 'container': 'article', 'title_sel': 'h3 a', 'date_sel': '.post-meta', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},

    # media_body pattern - House sites with media-body class (200+ members)
    'adriansmith': {'method': 'media_body', 'url_base': 'https://adriansmith.house.gov/media/press-releases'},
    'carson': {'method': 'media_body', 'url_base': 'https://carson.house.gov/media/press-releases'},
    'cisneros': {'method': 'media_body', 'url_base': 'https://cisneros.house.gov/media/press-releases'},
    'cohen': {'method': 'media_body', 'url_base': 'https://cohen.house.gov/media-center/press-releases'},
    'conaway': {'method': 'media_body', 'url_base': 'https://conaway.house.gov/media/press-releases'},
    'hamadeh': {'method': 'generic', 'url_base': 'https://hamadeh.house.gov/news/documentquery.aspx', 'container': 'div.article_wrap', 'title_sel': '.article_title', 'link_sel': 'a.link-block', 'date_sel': '.article_date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'issa': {'method': 'media_body', 'url_base': 'https://issa.house.gov/media/press-releases'},
    'keating': {'method': 'media_body', 'url_base': 'https://keating.house.gov/media/press-releases'},
    'kelly': {'method': 'media_body', 'url_base': 'https://kelly.house.gov/media/press-releases'},
    'kennedy': {'method': 'generic', 'url_base': 'https://kennedy.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'date_attr': 'datetime', 'pagination': '&page={page}'},
    'krishnamoorthi': {'method': 'media_body', 'url_base': 'https://krishnamoorthi.house.gov/media/press-releases'},
    'mcclintock': {'method': 'media_body', 'url_base': 'https://mcclintock.house.gov/newsroom/press-releases'},
    'mikekennedy': {'method': 'media_body', 'url_base': 'https://mikekennedy.house.gov/media/press-releases'},
    'moylan': {'method': 'media_body', 'url_base': 'https://moylan.house.gov/media/press-releases'},
    'onder': {'method': 'media_body', 'url_base': 'https://onder.house.gov/media/press-releases'},
    'patronis': {'method': 'media_body', 'url_base': 'https://patronis.house.gov/media/press-releases'},
    'radewagen': {'method': 'media_body', 'url_base': 'https://radewagen.house.gov/media/press-releases'},
    'schmidt': {'method': 'media_body', 'url_base': 'https://schmidt.house.gov/media/press-releases'},
    'soto': {'method': 'media_body', 'url_base': 'https://soto.house.gov/media/press-releases'},
    'summerlee': {'method': 'media_body', 'url_base': 'https://summerlee.house.gov/newsroom/press-releases'},
    'tenney': {'method': 'media_body', 'url_base': 'https://tenney.house.gov/media/press-releases'},
    'amodei': {'method': 'media_body', 'url_base': 'https://amodei.house.gov/news-releases'},
    'palmer': {'method': 'media_body', 'url_base': 'https://palmer.house.gov/media-center/press-releases'},
    'newhouse': {'method': 'media_body', 'url_base': 'https://newhouse.house.gov/media-center/press-releases'},
    'doggett': {'method': 'media_body', 'url_base': 'https://doggett.house.gov/media/press-releases'},
    'ocasio-cortez': {'method': 'media_body', 'url_base': 'https://ocasio-cortez.house.gov/media/press-releases'},
    'hudson': {'method': 'media_body', 'url_base': 'https://hudson.house.gov/media/press-releases'},
    'davis': {'method': 'media_body', 'url_base': 'https://davis.house.gov/media'},
    'espaillat': {'method': 'media_body', 'url_base': 'https://espaillat.house.gov/media/press-releases'},
    'algreen': {'method': 'media_body', 'url_base': 'https://algreen.house.gov/media/press-releases'},
    'mariodiazbalart': {'method': 'media_body', 'url_base': 'https://mariodiazbalart.house.gov/media-center/press-releases'},
    'biggs': {'method': 'media_body', 'url_base': 'https://biggs.house.gov/media/press-releases'},
    'johnjoyce': {'method': 'media_body', 'url_base': 'https://johnjoyce.house.gov/media/press-releases'},
    'larson': {'method': 'media_body', 'url_base': 'https://larson.house.gov/media-center/press-releases'},
    'kaptur': {'method': 'media_body', 'url_base': 'https://kaptur.house.gov/media-center/press-releases'},
    'benniethompson': {'method': 'media_body', 'url_base': 'https://benniethompson.house.gov/media/press-releases'},
    'walberg': {'method': 'media_body', 'url_base': 'https://walberg.house.gov/media/press-releases'},
    'burchett': {'method': 'media_body', 'url_base': 'https://burchett.house.gov/media/press-releases'},
    'cline': {'method': 'generic', 'url_base': 'https://cline.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '&Page={page}', 'url_prefix': '/news/'},
    'golden': {'method': 'media_body', 'url_base': 'https://golden.house.gov/media/press-releases'},
    'harder': {'method': 'media_body', 'url_base': 'https://harder.house.gov/media/press-releases'},
    'dustyjohnson': {'method': 'media_body', 'url_base': 'https://dustyjohnson.house.gov/media/press-releases'},
    'meuser': {'method': 'media_body', 'url_base': 'https://meuser.house.gov/media/press-releases'},
    'miller': {'method': 'media_body', 'url_base': 'https://miller.house.gov/media/press-releases'},
    'johnrose': {'method': 'media_body', 'url_base': 'https://johnrose.house.gov/media/press-releases'},
    'roy': {'method': 'media_body', 'url_base': 'https://roy.house.gov/media/press-releases'},
    'steil': {'method': 'media_body', 'url_base': 'https://steil.house.gov/media/press-releases'},
    'schrier': {'method': 'media_body', 'url_base': 'https://schrier.house.gov/media/press-releases'},
    'scalise': {'method': 'media_body', 'url_base': 'https://scalise.house.gov/media/press-releases'},
    'neguse': {'method': 'media_body', 'url_base': 'https://neguse.house.gov/media/press-releases'},
    'boyle': {'method': 'media_body', 'url_base': 'https://boyle.house.gov/media-center/press-releases'},
    'smucker': {'method': 'media_body', 'url_base': 'https://smucker.house.gov/media/press-releases'},
    'waters': {'method': 'media_body', 'url_base': 'https://waters.house.gov/media-center/press-releases'},
    'khanna': {'method': 'media_body', 'url_base': 'https://khanna.house.gov/media/press-releases'},
    'pelosi': {'method': 'media_body', 'url_base': 'https://pelosi.house.gov/news/press-releases'},
    'shontelbrown': {'method': 'media_body', 'url_base': 'https://shontelbrown.house.gov/media/press-releases'},
    'stansbury': {'method': 'media_body', 'url_base': 'https://stansbury.house.gov/media/press-releases'},
    'troycarter': {'method': 'media_body', 'url_base': 'https://troycarter.house.gov/media/press-releases'},
    'letlow': {'method': 'media_body', 'url_base': 'https://letlow.house.gov/media/press-releases'},
    'matsui': {'method': 'media_body', 'url_base': 'https://matsui.house.gov/media'},
    'harris': {'method': 'media_body', 'url_base': 'https://harris.house.gov/media/press-releases'},
    'wagner': {'method': 'media_body', 'url_base': 'https://wagner.house.gov/media-center/press-releases'},
    'pappas': {'method': 'media_body', 'url_base': 'https://pappas.house.gov/media/press-releases'},
    'crow': {'method': 'media_body', 'url_base': 'https://crow.house.gov/news'},
    'chuygarcia': {'method': 'media_body', 'url_base': 'https://chuygarcia.house.gov/media/press-releases'},
    'omar': {'method': 'media_body', 'url_base': 'https://omar.house.gov/media/press-releases'},
    'underwood': {'method': 'media_body', 'url_base': 'https://underwood.house.gov/media/press-releases'},
    'casten': {'method': 'senate_drupal_newscontent', 'url_base': 'https://casten.house.gov/media/press-releases'},
    'fleischmann': {'method': 'media_body', 'url_base': 'https://fleischmann.house.gov/media/press-releases'},
    'stevens': {'method': 'media_body', 'url_base': 'https://stevens.house.gov/media/press-releases'},
    'guest': {'method': 'media_body', 'url_base': 'https://guest.house.gov/media/press-releases'},
    'morelle': {'method': 'media_body', 'url_base': 'https://morelle.house.gov/media/press-releases'},
    'beatty': {'method': 'media_body', 'url_base': 'https://beatty.house.gov/media-center/press-releases'},
    'robinkelly': {'method': 'media_body', 'url_base': 'https://robinkelly.house.gov/media-center/press-releases'},
    'moolenaar': {'method': 'media_body', 'url_base': 'https://moolenaar.house.gov/media-center/press-releases'},
    'adams': {'method': 'media_body', 'url_base': 'https://adams.house.gov/media-center/press-releases'},
    'mfume': {'method': 'media_body', 'url_base': 'https://mfume.house.gov/media/press-releases'},
    'tiffany': {'method': 'media_body', 'url_base': 'https://tiffany.house.gov/media/press-releases'},
    'thompson': {'method': 'media_body', 'url_base': 'https://thompson.house.gov/media-center/press-releases'},
    'barrymoore': {'method': 'media_body', 'url_base': 'https://barrymoore.house.gov/media/press-releases'},
    'obernolte': {'method': 'media_body', 'url_base': 'https://obernolte.house.gov/media/press-releases'},
    'boebert': {'method': 'media_body', 'url_base': 'https://boebert.house.gov/media/press-releases'},
    'cammack': {'method': 'media_body', 'url_base': 'https://cammack.house.gov/media/press-releases'},
    'salazar': {'method': 'media_body', 'url_base': 'https://salazar.house.gov/media/press-releases'},
    'hinson': {'method': 'media_body', 'url_base': 'https://hinson.house.gov/media/press-releases'},
    'millermeeks': {'method': 'media_body', 'url_base': 'https://millermeeks.house.gov/media/press-releases'},
    'feenstra': {'method': 'media_body', 'url_base': 'https://feenstra.house.gov/media/press-releases'},
    'marymiller': {'method': 'media_body', 'url_base': 'https://marymiller.house.gov/media/press-releases'},
    'mrvan': {'method': 'media_body', 'url_base': 'https://mrvan.house.gov/media/press-releases'},
    'spartz': {'method': 'media_body', 'url_base': 'https://spartz.house.gov/media/press-releases'},
    'mann': {'method': 'media_body', 'url_base': 'https://mann.house.gov/media/press-releases'},
    'garbarino': {'method': 'media_body', 'url_base': 'https://garbarino.house.gov/media/press-releases'},
    'malliotakis': {'method': 'media_body', 'url_base': 'https://malliotakis.house.gov/media/press-releases'},
    'bice': {'method': 'media_body', 'url_base': 'https://bice.house.gov/media/press-releases'},
    'bentz': {'method': 'media_body', 'url_base': 'https://bentz.house.gov/media/press-releases'},
    'mace': {'method': 'media_body', 'url_base': 'https://mace.house.gov/media/press-releases'},
    'harshbarger': {'method': 'media_body', 'url_base': 'https://harshbarger.house.gov/media/press-releases'},
    'blakemoore': {'method': 'senate_drupal_newscontent', 'url_base': 'https://blakemoore.house.gov/media/press-releases'},
    'fitzgerald': {'method': 'media_body', 'url_base': 'https://fitzgerald.house.gov/media/press-releases'},
    'flood': {'method': 'media_body', 'url_base': 'https://flood.house.gov/media/press-releases'},
    'patryan': {'method': 'media_body', 'url_base': 'https://patryan.house.gov/media/press-releases'},
    'kamlager-dove': {'method': 'media_body', 'url_base': 'https://kamlager-dove.house.gov/media/press-releases'},
    'robertgarcia': {'method': 'media_body', 'url_base': 'https://robertgarcia.house.gov/media/press-releases'},
    'bean': {'method': 'media_body', 'url_base': 'https://bean.house.gov/media/press-releases'},
    'mccormick': {'method': 'media_body', 'url_base': 'https://mccormick.house.gov/media/press-releases'},
    'mikecollins': {'method': 'media_body', 'url_base': 'https://collins.house.gov/media/press-releases'},
    'edwards': {'method': 'media_body', 'url_base': 'https://edwards.house.gov/media/press-releases'},
    'kean': {'method': 'media_body', 'url_base': 'https://kean.house.gov/media/press-releases'},
    'goldman': {'method': 'media_body', 'url_base': 'https://goldman.house.gov/media/press-releases'},
    'langworthy': {'method': 'media_body', 'url_base': 'https://langworthy.house.gov/media/press-releases'},
    'magaziner': {'method': 'media_body', 'url_base': 'https://magaziner.house.gov/media/press-releases'},
    'vanorden': {'method': 'media_body', 'url_base': 'https://vanorden.house.gov/media/press-releases'},
    'hunt': {'method': 'media_body', 'url_base': 'https://hunt.house.gov/media/press-releases'},
    'casar': {'method': 'media_body', 'url_base': 'https://casar.house.gov/media/press-releases'},
    'crockett': {'method': 'media_body', 'url_base': 'https://crockett.house.gov/media/press-releases'},
    'luttrell': {'method': 'media_body', 'url_base': 'https://luttrell.house.gov/media/press-releases'},
    'deluzio': {'method': 'media_body', 'url_base': 'https://deluzio.house.gov/media/press-releases'},
    'lalota': {'method': 'media_body', 'url_base': 'https://lalota.house.gov/media/press-releases'},
    'vargas': {'method': 'media_body', 'url_base': 'https://vargas.house.gov/media/press-releases'},
    'vasquez': {'method': 'media_body', 'url_base': 'https://vasquez.house.gov/media/press-releases'},
    'scholten': {'method': 'media_body', 'url_base': 'https://scholten.house.gov/media/press-releases'},
    'ivey': {'method': 'media_body', 'url_base': 'https://ivey.house.gov/media/press-releases'},
    'sorensen': {'method': 'media_body', 'url_base': 'https://sorensen.house.gov/media/press-releases'},
    'nunn': {'method': 'generic', 'url_base': 'https://nunn.house.gov/category/news/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h1.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'laurellee': {'method': 'media_body', 'url_base': 'https://laurellee.house.gov/media/press-releases'},
    'mills': {'method': 'media_body', 'url_base': 'https://mills.house.gov/media/press-releases'},
    'ciscomani': {'method': 'media_body', 'url_base': 'https://ciscomani.house.gov/media/press-releases'},
    'horsford': {'method': 'media_body', 'url_base': 'https://horsford.house.gov/media/press-releases'},
    'cleaver': {'method': 'media_body', 'url_base': 'https://cleaver.house.gov/media-center/press-releases'},
    'aderholt': {'method': 'media_body', 'url_base': 'https://aderholt.house.gov/media-center/press-releases'},
    'courtney': {'method': 'media_body', 'url_base': 'https://courtney.house.gov/media-center/press-releases'},
    'stauber': {'method': 'media_body', 'url_base': 'https://stauber.house.gov/media/press-releases'},
    'mccaul': {'method': 'media_body', 'url_base': 'https://mccaul.house.gov/media-center/press-releases'},
    'foster': {'method': 'media_body', 'url_base': 'https://foster.house.gov/media/press-releases'},
    'schakowsky': {'method': 'media_body', 'url_base': 'https://schakowsky.house.gov/media/press-releases'},
    'craig': {'method': 'media_body', 'url_base': 'https://craig.house.gov/media/press-releases'},
    'desaulnier': {'method': 'media_body', 'url_base': 'https://desaulnier.house.gov/media-center/press-releases'},
    'murphy': {'method': 'media_body', 'url_base': 'https://murphy.house.gov/media/press-releases'},
    'calvert': {'method': 'media_body', 'url_base': 'https://calvert.house.gov/media/press-releases'},
    'bobbyscott': {'method': 'media_body', 'url_base': 'https://bobbyscott.house.gov/media-center/press-releases'},
    'bilirakis': {'method': 'media_body', 'url_base': 'https://bilirakis.house.gov/media/press-releases'},
    'delauro': {'method': 'media_body', 'url_base': 'https://delauro.house.gov/media-center/press-releases'},
    'norton': {'method': 'media_body', 'url_base': 'https://norton.house.gov/media/press-releases'},
    'mikethompson': {'method': 'media_body', 'url_base': 'https://mikethompson.house.gov/newsroom/press-releases'},
    'degette': {'method': 'media_body', 'url_base': 'https://degette.house.gov/media-center/press-releases'},
    'ruiz': {'method': 'media_body', 'url_base': 'https://ruiz.house.gov/media-center/press-releases'},
    'sherman': {'method': 'media_body', 'url_base': 'https://sherman.house.gov/media-center/press-releases'},
    'quigley': {'method': 'media_body', 'url_base': 'https://quigley.house.gov/media-center/press-releases'},
    'panetta': {'method': 'media_body', 'url_base': 'https://panetta.house.gov/media/press-releases'},
    'schneider': {'method': 'media_body', 'url_base': 'https://schneider.house.gov/media/press-releases'},
    'sylviagarcia': {'method': 'media_body', 'url_base': 'https://sylviagarcia.house.gov/media/press-releases'},
    'susielee': {'method': 'media_body', 'url_base': 'https://susielee.house.gov/media/press-releases'},
    'amo': {'method': 'media_body', 'url_base': 'https://amo.house.gov/press-releases'},
    'mcclellan': {'method': 'generic', 'url_base': 'https://mcclellan.house.gov/category/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h3 a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'rulli': {'method': 'generic', 'url_base': 'https://rulli.house.gov/category/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'suozzi': {'method': 'media_body', 'url_base': 'https://suozzi.house.gov/media/press-releases'},
    'fong': {'method': 'media_body', 'url_base': 'https://fong.house.gov/media/press-releases'},
    'mciver': {'method': 'senate_drupal_newscontent', 'url_base': 'https://mciver.house.gov/media/press-releases'},
    'westerman': {'method': 'media_body', 'url_base': 'https://westerman.house.gov/media-center/press-releases'},
    'wied': {'method': 'media_body', 'url_base': 'https://wied.house.gov/media/press-releases'},
    'moulton': {'method': 'media_body', 'url_base': 'https://moulton.house.gov/news/press-releases'},
    'nehls': {'method': 'media_body', 'url_base': 'https://nehls.house.gov/media'},
    'meng': {'method': 'media_body', 'url_base': 'https://meng.house.gov/media-center/press-releases'},
    'lindasanchez': {'method': 'media_body', 'url_base': 'https://lindasanchez.house.gov/media-center/press-releases'},
    'dondavis': {'method': 'media_body', 'url_base': 'https://dondavis.house.gov/media/press-releases'},
    'strong': {'method': 'media_body', 'url_base': 'https://strong.house.gov/media/press-releases'},
    'chu': {'method': 'media_body', 'url_base': 'https://chu.house.gov/media-center/press-releases'},
    'lieu': {'method': 'media_body', 'url_base': 'https://lieu.house.gov/media-center/press-releases'},
    'joewilson': {'method': 'media_body', 'url_base': 'https://joewilson.house.gov/media/press-releases'},
    'zinke': {'method': 'media_body', 'url_base': 'https://zinke.house.gov/media/press-releases'},
    'rutherford': {'method': 'media_body', 'url_base': 'https://rutherford.house.gov/media/press-releases'},
    'veasey': {'method': 'media_body', 'url_base': 'https://veasey.house.gov/media-center/press-releases'},
    'garamendi': {'method': 'generic', 'url_base': 'https://garamendi.house.gov/category/press-release/', 'container': 'a.item', 'title_sel': '.title', 'date_sel': '.date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'kustoff': {'method': 'media_body', 'url_base': 'https://kustoff.house.gov/media/press-releases'},
    'gonzalez': {'method': 'media_body', 'url_base': 'https://gonzalez.house.gov/media/press-releases'},
    'costa': {'method': 'media_body', 'url_base': 'https://costa.house.gov/media/press-releases'},
    'houchin': {'method': 'media_body', 'url_base': 'https://houchin.house.gov/media/press-releases'},
    'williams': {'method': 'media_body', 'url_base': 'https://williams.house.gov/media-center/press-releases'},
    'wilson': {'method': 'media_body', 'url_base': 'https://wilson.house.gov/media/press-releases'},
    'menendez': {'method': 'senate_drupal_newscontent', 'url_base': 'https://menendez.house.gov/media/press-releases'},
    'pocan': {'method': 'media_body', 'url_base': 'https://pocan.house.gov/media-center/press-releases'},
    'ogles': {'method': 'media_body', 'url_base': 'https://ogles.house.gov/media/press-releases'},
    'velazquez': {'method': 'media_body', 'url_base': 'https://velazquez.house.gov/media-center/press-releases'},
    'bonamici': {'method': 'media_body', 'url_base': 'https://bonamici.house.gov/media/press-releases'},
    'keithself': {'method': 'media_body', 'url_base': 'https://keithself.house.gov/media/press-releases'},
    'bishop': {'method': 'media_body', 'url_base': 'https://bishop.house.gov/media-center/press-releases'},
    'hoyer': {'method': 'media_body', 'url_base': 'https://hoyer.house.gov/media'},
    'burlison': {'method': 'media_body', 'url_base': 'https://burlison.house.gov/media/press-releases'},
    'jonathanjackson': {'method': 'media_body', 'url_base': 'https://jonathanjackson.house.gov/media/press-releases'},
    'davids': {'method': 'media_body', 'url_base': 'https://davids.house.gov/media/press-releases'},
    'mccollum': {'method': 'media_body', 'url_base': 'https://mccollum.house.gov/media/press-releases'},
    'adamsmith': {'method': 'media_body', 'url_base': 'https://adamsmith.house.gov/news/press-releases'},
    'hankjohnson': {'method': 'media_body', 'url_base': 'https://hankjohnson.house.gov/media-center/press-releases'},
    'evans': {'method': 'media_body', 'url_base': 'https://evans.house.gov/media/press-releases'},
    'salinas': {'method': 'media_body', 'url_base': 'https://salinas.house.gov/media/press-releases'},
    'pallone': {'method': 'media_body', 'url_base': 'https://pallone.house.gov/media/press-releases'},
    'ramirez': {'method': 'media_body', 'url_base': 'https://ramirez.house.gov/media/press-releases'},
    'graves': {'method': 'media_body', 'url_base': 'https://graves.house.gov/media/press-releases'},
    'cole': {'method': 'media_body', 'url_base': 'https://cole.house.gov/media-center/press-releases'},
    'jordan': {'method': 'media_body', 'url_base': 'https://jordan.house.gov/media/press-releases'},
    'hageman': {'method': 'media_body', 'url_base': 'https://hageman.house.gov/media/press-releases'},
    'figures': {'method': 'media_body', 'url_base': 'https://figures.house.gov/media'},
    'begich': {'method': 'media_body', 'url_base': 'https://begich.house.gov/media/press-releases'},
    'simon': {'method': 'media_body', 'url_base': 'https://simon.house.gov/media/press-releases'},
    'gray': {'method': 'media_body', 'url_base': 'https://gray.house.gov/media/press-releases'},
    'liccardo': {'method': 'media_body', 'url_base': 'https://liccardo.house.gov/media/press-releases'},
    'rivas': {'method': 'media_body', 'url_base': 'https://rivas.house.gov/media/press-releases'},
    'friedman': {'method': 'media_body', 'url_base': 'https://friedman.house.gov/media/press-releases'},
    'tran': {'method': 'media_body', 'url_base': 'https://tran.house.gov/media/press-releases'},
    'min': {'method': 'media_body', 'url_base': 'https://min.house.gov/media/press-releases'},
    'hurd': {'method': 'media_body', 'url_base': 'https://hurd.house.gov/media/press-releases'},
    'crank': {'method': 'media_body', 'url_base': 'https://crank.house.gov/media/press-releases'},
    'gabeevans': {'method': 'media_body', 'url_base': 'https://gabeevans.house.gov/media/press-releases'},
    'mcbride': {'method': 'media_body', 'url_base': 'https://mcbride.house.gov/media/press-releases'},
    'haridopolos': {'method': 'media_body', 'url_base': 'https://haridopolos.house.gov/media/press-releases'},
    'jack': {'method': 'media_body', 'url_base': 'https://jack.house.gov/media/press-releases'},
    'stutzman': {'method': 'media_body', 'url_base': 'https://stutzman.house.gov/media/press-releases'},
    'shreve': {'method': 'media_body', 'url_base': 'https://shreve.house.gov/media/press-releases'},
    'fields': {'method': 'media_body', 'url_base': 'https://fields.house.gov/media/press-releases'},
    'olszewski': {'method': 'media_body', 'url_base': 'https://olszewski.house.gov/media/press-releases'},
    'elfreth': {'method': 'media_body', 'url_base': 'https://elfreth.house.gov/media/press-releases'},
    'mcclaindelaney': {'method': 'media_body', 'url_base': 'https://mcclaindelaney.house.gov/media/press-releases'},
    'mcdonaldrivet': {'method': 'media_body', 'url_base': 'https://mcdonaldrivet.house.gov/media/press-releases'},
    'barrett': {'method': 'media_body', 'url_base': 'https://barrett.house.gov/media/press-releases'},
    'morrison': {'method': 'media_body', 'url_base': 'https://morrison.house.gov/media/press-releases'},
    'bell': {'method': 'media_body', 'url_base': 'https://bell.house.gov/media/press-releases'},
    'downing': {'method': 'media_body', 'url_base': 'https://downing.house.gov/media/press-releases'},
    'goodlander': {'method': 'generic', 'url_base': 'https://goodlander.house.gov/media/press-releases/', 'container': 'li.post', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%dT%H:%M:%S+00:00'], 'pagination': '?query-79-page={page}'},
    'pou': {'method': 'media_body', 'url_base': 'https://pou.house.gov/media/press-releases'},
    'gillen': {'method': 'media_body', 'url_base': 'https://gillen.house.gov/media/press-releases'},
    'latimer': {'method': 'media_body', 'url_base': 'https://latimer.house.gov/media/press-releases'},
    'riley': {'method': 'generic', 'url_base': 'https://riley.house.gov/news/', 'container': 'article.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'mannion': {'method': 'media_body', 'url_base': 'https://mannion.house.gov/media/press-releases'},
    'mcdowell': {'method': 'media_body', 'url_base': 'https://mcdowell.house.gov/media/press-releases'},
    'markharris': {'method': 'media_body', 'url_base': 'https://markharris.house.gov/media/press-releases'},
    'harrigan': {'method': 'media_body', 'url_base': 'https://harrigan.house.gov/media/press-releases'},
    'knott': {'method': 'media_body', 'url_base': 'https://knott.house.gov/media/press-releases'},
    'timmoore': {'method': 'media_body', 'url_base': 'https://timmoore.house.gov/media/press-releases'},
    'fedorchak': {'method': 'media_body', 'url_base': 'https://fedorchak.house.gov/media/press-releases'},
    'king-hinds': {'method': 'media_body', 'url_base': 'https://king-hinds.house.gov/media'},
    'taylor': {'method': 'media_body', 'url_base': 'https://taylor.house.gov/media/press-releases'},
    'dexter': {'method': 'media_body', 'url_base': 'https://dexter.house.gov/media/press-releases'},
    'bynum': {'method': 'media_body', 'url_base': 'https://bynum.house.gov/media/press-releases'},
    'mackenzie': {'method': 'media_body', 'url_base': 'https://mackenzie.house.gov/media/press-releases'},
    'bresnahan': {'method': 'media_body', 'url_base': 'https://bresnahan.house.gov/media'},
    'hernandez': {'method': 'media_body', 'url_base': 'https://hernandez.house.gov/media/press-releases'},
    'sheribiggs': {'method': 'media_body', 'url_base': 'https://sheribiggs.house.gov/media/press-releases'},
    'craiggoldman': {'method': 'media_body', 'url_base': 'https://craiggoldman.house.gov/media/press-releases'},
    'gill': {'method': 'media_body', 'url_base': 'https://gill.house.gov/media/press-releases'},
    'juliejohnson': {'method': 'media_body', 'url_base': 'https://juliejohnson.house.gov/media/press-releases'},
    'mcguire': {'method': 'media_body', 'url_base': 'https://mcguire.house.gov/media/press-releases'},
    'vindman': {'method': 'generic', 'url_base': 'https://vindman.house.gov/category/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'subramanyam': {'method': 'media_body', 'url_base': 'https://subramanyam.house.gov/media/press-releases'},
    'baumgartner': {'method': 'generic', 'url_base': 'https://baumgartner.house.gov/category/press-releases/', 'container': 'div.post-list a.item', 'title_sel': '.title', 'date_sel': '.date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'randall': {'method': 'media_body', 'url_base': 'https://randall.house.gov/media/press-releases'},
    'rileymoore': {'method': 'media_body', 'url_base': 'https://rileymoore.house.gov/media/press-releases'},

    # generic pattern - Universal config-driven scrapers
    # ArticleBlock pattern with h2 a title, p date, %m.%d.%Y format
    'baldwin': {'method': 'generic', 'url_base': 'https://www.baldwin.senate.gov/news/press-releases', 'container': 'div.ArticleBlock', 'title_sel': 'h2.ArticleTitle', 'link_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%m.%d.%y', '%m.%d.%Y', '%m/%d/%y', '%B %d, %Y'], 'pagination': '?PageNum_rs={page}&'},
    'schumer': {'method': 'generic', 'url_base': 'https://www.schumer.senate.gov/newsroom/press-releases', 'container': 'div.ArticleBlock', 'title_sel': '.ArticleTitle', 'link_sel': 'a', 'date_sel': 'p.Heading--time', 'date_fmt': ['%B %d, %Y', '%m.%d.%y', '%m.%d.%Y', '%m/%d/%y'], 'pagination': '?PageNum_rs={page}&'},
    'grassley': {'method': 'generic', 'url_base': 'https://www.grassley.senate.gov/news/news-releases', 'container': 'li.PageList__item', 'title_sel': 'a.PressBlock__title', 'date_sel': 'p.PressBlock__date', 'date_fmt': ['%m.%d.%Y', '%m/%d/%y', '%B %d, %Y'], 'pagination': '?pagenum_rs={page}'},

    # documentquery.aspx pattern - House sites with span.middot date
    'bacon': {'method': 'generic', 'url_base': 'https://bacon.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'bera': {'method': 'media_body', 'url_base': 'https://bera.house.gov/news'},
    'castor': {'method': 'generic', 'url_base': 'https://castor.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?DocumentTypeID=821&Page={page}', 'url_prefix': '/news/'},
    'emmer': {'method': 'generic', 'url_base': 'https://emmer.house.gov/media-center/press-releases', 'container': '.media-body', 'title_sel': 'div.h3 a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'foxx': {'method': 'generic', 'url_base': 'https://foxx.house.gov/news/documentquery.aspx', 'container': 'article.newsblocker', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=2367&Page={page}', 'url_prefix': '/news/'},
    'gosar': {'method': 'generic', 'url_base': 'https://gosar.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'houlahan': {'method': 'rss', 'url_base': 'https://houlahan.house.gov/news/rss.aspx'},
    'huizenga': {'method': 'generic', 'url_base': 'https://huizenga.house.gov/news/documentquery.aspx', 'container': 'article.newsblocker', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d', '%B %d, %Y'], 'pagination': '?DocumentTypeID=2041&Page={page}', 'url_prefix': '/news/'},
    'jasonsmith': {'method': 'generic', 'url_base': 'https://jasonsmith.house.gov/category/press_release/', 'container': 'a.item', 'title_sel': 'h3', 'date_sel': 'span.date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'larsen': {'method': 'generic', 'url_base': 'https://larsen.house.gov/news/documentquery.aspx', 'container': '.news-texthold', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'mast': {'method': 'generic', 'url_base': 'https://mast.house.gov/press-releases', 'container': 'table tr', 'title_sel': 'a.ContentGrid', 'date_sel': 'td.recordListDate', 'date_fmt': ['%m/%d/%y', '%m/%d/%Y'], 'skip_first': 1, 'pagination': '?PageNum_rs={page}', 'base_domain': 'mast.house.gov'},
    'mcgovern': {'method': 'generic', 'url_base': 'https://mcgovern.house.gov/news/documentquery.aspx', 'container': 'article.newsblocker', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d', '%B %d, %Y'], 'pagination': '?DocumentTypeID=2472&Page={page}', 'url_prefix': '/news/'},
    'norcross': {'method': 'generic', 'url_base': 'https://norcross.house.gov/press-releases', 'container': 'div.media-digest-body', 'title_sel': 'a.media-digest-body-link', 'date_sel': 'div.media-digest-header', 'base_domain': 'norcross.house.gov'},
    'schweikert': {'method': 'generic', 'url_base': 'https://schweikert.house.gov/category/congress_press_release/', 'container': 'div.post-content', 'title_sel': 'h2 a', 'date_sel': 'span.date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'titus': {'method': 'generic', 'url_base': 'https://titus.house.gov/news/documentquery.aspx', 'container': 'article.newsblocker', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'tlaib': {'method': 'react', 'url_base': 'https://tlaib.house.gov/resources/press'},
    'tonko': {'method': 'generic', 'url_base': 'https://tonko.house.gov/news/documentquery.aspx', 'container': '.news-texthold', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'trentkelly': {'method': 'generic', 'url_base': 'https://trentkelly.house.gov/newsroom/documentquery.aspx', 'container': 'article', 'title_sel': 'h3', 'link_sel': 'a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/newsroom/'},

    # et_pb_post / Divi theme pattern - Senate sites
    'budd': {'method': 'generic', 'url_base': 'https://www.budd.senate.gov/category/news/press-releases/page/', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'p span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/?et_blog'},
    'hagerty': {'method': 'generic', 'url_base': 'https://www.hagerty.senate.gov/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'p span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': '?et_blog&sf_paged={page}'},
    'gillibrand': {'method': 'generic', 'url_base': 'https://www.gillibrand.senate.gov/press-releases/page/', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y', '%B %d, %Y'], 'pagination': '{page}/', 'skip_first': 1},
    'lummis': {'method': 'generic', 'url_base': 'https://www.lummis.senate.gov/press-releases/page/', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'p span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/?et_blog'},

    # WordPress category pattern
    'jeffries': {'method': 'generic', 'url_base': 'https://jeffries.house.gov/category/press-release/page/', 'container': 'article', 'title_sel': 'h1', 'link_sel': 'a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}', 'max_results': 10},
    'murray': {'method': 'generic', 'url_base': 'https://www.murray.senate.gov/category/press-releases/', 'container': 'article.elementor-post', 'title_sel': 'h2.elementor-post__title a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'rickscott': {'method': 'generic', 'url_base': 'https://www.rickscott.senate.gov/press-releases/', 'container': 'div.element', 'title_sel': 'div.element-title', 'link_sel': 'a', 'date_sel': 'span.element-date', 'date_fmt': ['%b %d']},
    'welch': {'method': 'generic', 'url_base': 'https://www.welch.senate.gov/category/press-release/page/', 'container': 'article', 'title_sel': 'h2', 'link_sel': 'a', 'date_sel': '.postDate span', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},

    # Jet listing / Elementor pattern - converted to generic
    'britt': {'method': 'generic', 'url_base': 'https://www.britt.senate.gov/media/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h3 a', 'date_sel': 'h3.elementor-heading-title', 'date_fmt': ['%m.%d.%Y', '%m/%d/%Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'fetterman': {'method': 'generic', 'url_base': 'https://www.fetterman.senate.gov/press-release/', 'container': 'article.elementor-post', 'title_sel': 'h3.elementor-post__title a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'jayapal': {'method': 'generic', 'url_base': 'https://jayapal.house.gov/category/press-releases/', 'container': 'article.post-item', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%m.%d.%Y'], 'pagination': 'page/{page}/'},
    'markkelly': {'method': 'generic', 'url_base': 'https://www.kelly.senate.gov/newsroom/press-releases/', 'container': 'div.jet-listing-grid__item', 'title_sel': 'h3 a', 'date_sel': 'span.elementor-post-info__item--type-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'tuberville': {'method': 'generic', 'url_base': 'https://www.tuberville.senate.gov/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h4 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},

    # Table-based pattern - House sites with tr containers
    'barr': {'method': 'table_recordlist_date', 'url_base': 'https://barr.house.gov/press-releases'},
    'clarke': {'method': 'generic', 'url_base': 'https://clarke.house.gov/category/press-release/', 'container': '.post', 'title_sel': 'h2', 'link_sel': 'a', 'date_sel': 'span.date', 'date_fmt': ['%m/%d/%y'], 'pagination': 'page/{page}/'},
    'crawford': {'method': 'generic', 'url_base': 'https://crawford.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': '.h3 a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'grijalva': {'method': 'generic', 'url_base': 'https://grijalva.house.gov/media', 'container': '.media-body', 'title_sel': 'div.h3 a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'scanlon': {'method': 'generic', 'url_base': 'https://scanlon.house.gov/news/documentquery.aspx', 'container': 'article.newsblocker', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'takano': {'method': 'senate_drupal_newscontent', 'url_base': 'https://takano.house.gov/newsroom/press-releases'},

    # CFM table pattern - Senate sites with index.cfm
    'bennet': {'method': 'generic', 'url_base': 'https://www.bennet.senate.gov/news/page/', 'container': 'article.et_pb_post', 'title_sel': 'h3 a', 'date_sel': 'p span.published', 'date_fmt': ['%B %d, %Y', '%b %d, %Y'], 'pagination': '{page}/?et_blog'},
    'hoeven': {'method': 'generic', 'url_base': 'https://www.hoeven.senate.gov/newsroom/press-releases', 'container': '.ArticleBlock', 'title_sel': 'h3', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'warner': {'method': 'generic', 'url_base': 'https://www.warner.senate.gov/news/press-releases/', 'container': 'div.e-loop-item', 'title_sel': 'h3 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?e-page-8fc628f={page}'},

    # Other convertible patterns
    'angusking': {'method': 'generic', 'url_base': 'https://www.king.senate.gov/newsroom/press-releases/table', 'container': '.press-browser__item-row', 'title_sel': 'a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?pagenum_rs={page}'},
    'barragan': {'method': 'generic', 'url_base': 'https://barragan.house.gov/news', 'container': '.post', 'title_sel': 'h2', 'link_sel': 'a.btn', 'date_sel': 'p.date', 'date_fmt': ['%B %d, %Y'], 'pagination': '/page/{page}/'},
    'clyburn': {'method': 'generic', 'url_base': 'https://clyburn.house.gov/press-releases/', 'container': 'article.elementor-post', 'title_sel': 'h2 a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'hawley': {'method': 'generic', 'url_base': 'https://www.hawley.senate.gov/press-releases/page/', 'container': 'article .post', 'title_sel': 'h2 a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},
    'meeks': {'method': 'generic', 'url_base': 'https://meeks.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': 'a.h4', 'date_sel': '.evo-card-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1, 'max_results': 10},
    'steube': {'method': 'generic', 'url_base': 'https://steube.house.gov/category/press-releases/page/', 'container': 'article.item', 'title_sel': 'h3', 'link_sel': 'a', 'date_sel': 'span.date', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},
    'sykes': {'method': 'generic', 'url_base': 'https://sykes.house.gov/media/press-releases', 'container': 'table#browser_table tbody tr', 'title_sel': 'a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'tinasmith': {'method': 'generic', 'url_base': 'https://www.smith.senate.gov/press-releases/', 'container': 'article.elementor-post', 'title_sel': 'h3.elementor-post__title a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '{page}/'},
    'vanhollen': {'method': 'generic', 'url_base': 'https://www.vanhollen.senate.gov/news/press-releases', 'container': 'ul li.PageList__item', 'title_sel': 'a', 'date_sel': 'p', 'date_fmt': ['%m/%d/%y', '%m.%d.%y'], 'pagination': '?pagenum_rs={page}'},

    # --- New scrapers added by find_missing_scrapers.py ---
    'alford': {'method': 'generic', 'url_base': 'https://alford.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'allen': {'method': 'generic', 'url_base': 'https://allen.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'arrington': {'method': 'generic', 'url_base': 'https://arrington.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d', '%B %d, %Y'], 'pagination': '&Page={page}', 'url_prefix': '/news/'},
    'babin': {'method': 'generic', 'url_base': 'https://babin.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'baird': {'method': 'generic', 'url_base': 'https://baird.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'balint': {'method': 'generic', 'url_base': 'https://balint.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'beyer': {'method': 'generic', 'url_base': 'https://beyer.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'bost': {'method': 'table_recordlist_date', 'url_base': 'https://bost.house.gov/press-releases'},
    'brecheen': {'method': 'generic', 'url_base': 'https://brecheen.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'buddycarter': {'method': 'generic', 'url_base': 'https://buddycarter.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'carbajal': {'method': 'generic', 'url_base': 'https://carbajal.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'carter': {'method': 'generic', 'url_base': 'https://carter.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'clyde': {'method': 'generic', 'url_base': 'https://clyde.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'comer': {'method': 'table_recordlist_date', 'url_base': 'https://comer.house.gov/media'},
    'crenshaw': {'method': 'table_recordlist_date', 'url_base': 'https://crenshaw.house.gov/press-releases'},
    'cuellar': {'method': 'generic', 'url_base': 'https://cuellar.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'curtis': {'method': 'generic', 'url_base': 'https://www.curtis.senate.gov/newsroom/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}'},
    'davidson': {'method': 'table_recordlist_date', 'url_base': 'https://davidson.house.gov/press-releases'},
    'dean': {'method': 'table_recordlist_date', 'url_base': 'https://dean.house.gov/press-releases'},
    'debbiedingell': {'method': 'generic', 'url_base': 'https://debbiedingell.house.gov/media-center/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'delacruz': {'method': 'generic', 'url_base': 'https://delacruz.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'delbene': {'method': 'generic', 'url_base': 'https://delbene.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'donalds': {'method': 'generic', 'url_base': 'https://donalds.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'dunn': {'method': 'generic', 'url_base': 'https://dunn.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'escobar': {'method': 'generic', 'url_base': 'https://escobar.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'estes': {'method': 'generic', 'url_base': 'https://estes.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'ezell': {'method': 'generic', 'url_base': 'https://ezell.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'fallon': {'method': 'generic', 'url_base': 'https://fallon.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'fernandez': {'method': 'generic', 'url_base': 'https://fernandez.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'fine': {'method': 'generic', 'url_base': 'https://fine.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'finstad': {'method': 'generic', 'url_base': 'https://finstad.house.gov/media', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'p span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}'},
    'fischbach': {'method': 'table_recordlist_date', 'url_base': 'https://fischbach.house.gov/press-releases'},
    'frankel': {'method': 'generic', 'url_base': 'https://frankel.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'franklin': {'method': 'generic', 'url_base': 'https://franklin.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'fry': {'method': 'generic', 'url_base': 'https://fry.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'gomez': {'method': 'generic', 'url_base': 'https://gomez.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'grothman': {'method': 'generic', 'url_base': 'https://grothman.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'guthrie': {'method': 'generic', 'url_base': 'https://guthrie.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'gwenmoore': {'method': 'generic', 'url_base': 'https://gwenmoore.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'halrogers': {'method': 'table_recordlist_date', 'url_base': 'https://halrogers.house.gov/press-releases'},
    'hill': {'method': 'generic', 'url_base': 'https://hill.house.gov/media-center/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'jackson': {'method': 'generic', 'url_base': 'https://jackson.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'james': {'method': 'generic', 'url_base': 'https://james.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'justice': {'method': 'generic', 'url_base': 'https://www.justice.senate.gov/newsroom/press-releases/', 'container': 'div.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?e-page-13b5287={page}'},
    'kim': {'method': 'generic', 'url_base': 'https://www.kim.senate.gov/newsroom/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y', '%B %d, %Y'], 'pagination': '', 'skip_first': 1},
    'lahood': {'method': 'table_recordlist_date', 'url_base': 'https://lahood.house.gov/press-releases'},
    'latta': {'method': 'generic', 'url_base': 'https://latta.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'lawler': {'method': 'generic', 'url_base': 'https://lawler.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'loudermilk': {'method': 'generic', 'url_base': 'https://loudermilk.house.gov/category/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'lynch': {'method': 'table_recordlist_date', 'url_base': 'https://lynch.house.gov/press-releases'},
    'maloy': {'method': 'generic', 'url_base': 'https://maloy.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'massie': {'method': 'generic', 'url_base': 'https://massie.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'mcbath': {'method': 'generic', 'url_base': 'https://mcbath.house.gov/category/press-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/?et_blog'},
    'mcclain': {'method': 'table_recordlist_date', 'url_base': 'https://mcclain.house.gov/press-releases'},
    'menefee': {'method': 'generic', 'url_base': 'https://menefee.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': '.media-body a', 'date_sel': '.media-body .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'messmer': {'method': 'generic', 'url_base': 'https://messmer.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'mikejohnson': {'method': 'generic', 'url_base': 'https://mikejohnson.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'mikerogers': {'method': 'generic', 'url_base': 'https://mikerogers.house.gov/media-center/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'moody': {'method': 'generic', 'url_base': 'https://www.moody.senate.gov/press-releases', 'container': 'article.et_pb_post', 'title_sel': 'h2 a', 'date_sel': 'p span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}'},
    'moreno': {'method': 'generic', 'url_base': 'https://www.moreno.senate.gov/newsroom/press-releases', 'container': 'div.e-loop-item', 'title_sel': '.elementor-heading-title a', 'date_sel': '.elementor-heading-title', 'date_fmt': ['%B %d, %Y'], 'pagination': '?e-page-1687717={page}'},
    'morgangriffith': {'method': 'generic', 'url_base': 'https://morgangriffith.house.gov/news/', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d', '%B %d, %Y'], 'pagination': '?page={page}', 'url_prefix': '/news/'},
    'nadler': {'method': 'generic', 'url_base': 'https://nadler.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'nathanielmoran': {'method': 'generic', 'url_base': 'https://moran.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'norman': {'method': 'generic', 'url_base': 'https://norman.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'perry': {'method': 'generic', 'url_base': 'https://perry.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'pettersen': {'method': 'generic', 'url_base': 'https://pettersen.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'pfluger': {'method': 'generic', 'url_base': 'https://pfluger.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'pingree': {'method': 'generic', 'url_base': 'https://pingree.house.gov/media-center/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'plaskett': {'method': 'generic', 'url_base': 'https://plaskett.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'raskin': {'method': 'table_recordlist_date', 'url_base': 'https://raskin.house.gov/press-releases'},
    'rosen': {'method': 'generic', 'url_base': 'https://www.rosen.senate.gov/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'span.elementor-post-date', 'date_fmt': ['%m/%d/%Y', '%B %d, %Y'], 'pagination': ''},
    'ross': {'method': 'table_recordlist_date', 'url_base': 'https://ross.house.gov/press-releases'},
    'rouzer': {'method': 'generic', 'url_base': 'https://rouzer.house.gov/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'schmitt': {'method': 'generic', 'url_base': 'https://www.schmitt.senate.gov/media/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'a.jet-listing-dynamic-link__link', 'date_sel': '.overline h3', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'scottpeters': {'method': 'media_body', 'url_base': 'https://scottpeters.house.gov/press-releases'},
    'sessions': {'method': 'table_recordlist_date', 'url_base': 'https://sessions.house.gov/press-releases'},
    'sewell': {'method': 'table_recordlist_date', 'url_base': 'https://sewell.house.gov/press-releases'},
    'simpson': {'method': 'generic', 'url_base': 'https://simpson.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'stanton': {'method': 'table_recordlist_date', 'url_base': 'https://stanton.house.gov/press-releases'},
    'stefanik': {'method': 'table_recordlist_date', 'url_base': 'https://stefanik.house.gov/press-releases'},
    'timkennedy': {'method': 'generic', 'url_base': 'https://kennedy.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'timmons': {'method': 'generic', 'url_base': 'https://timmons.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'trahan': {'method': 'generic', 'url_base': 'https://trahan.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'turner': {'method': 'media_body', 'url_base': 'https://turner.house.gov/media-center/press-releases'},
    'valadao': {'method': 'generic', 'url_base': 'https://valadao.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'vandrew': {'method': 'generic', 'url_base': 'https://vandrew.house.gov/media/press-releases', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'vanduyne': {'method': 'table_recordlist_date', 'url_base': 'https://vanduyne.house.gov/press-releases'},
    'vanepps': {'method': 'generic', 'url_base': 'https://vanepps.house.gov/media/press-releases', 'container': '.views-row', 'title_sel': '.media-body a', 'date_sel': '.media-body .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'walkinshaw': {'method': 'generic', 'url_base': 'https://walkinshaw.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'weber': {'method': 'generic', 'url_base': 'https://weber.house.gov/news/documentquery.aspx?DocumentTypeID=27', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '&Page={page}'},
    'webster': {'method': 'table_recordlist_date', 'url_base': 'https://webster.house.gov/press-releases'},
    'wittman': {'method': 'generic', 'url_base': 'https://wittman.house.gov/newsroom/press-releases', 'container': '.views-row', 'title_sel': '.h3 a', 'date_sel': '.col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'womack': {'method': 'generic', 'url_base': 'https://womack.house.gov/news', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y', '%Y-%m-%d'], 'pagination': '?page={page}'},
    'youngkim': {'method': 'generic', 'url_base': 'https://youngkim.house.gov/media/press-releases/', 'container': '.et_pb_post', 'title_sel': 'h2.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    # Group 1: senate_drupal_newscontent (#newscontent h2 with span.date)
    'auchincloss': {'method': 'senate_drupal_newscontent', 'url_base': 'https://auchincloss.house.gov/media/press-releases'},
    'correa': {'method': 'senate_drupal_newscontent', 'url_base': 'https://correa.house.gov/news/press-releases'},
    'foushee': {'method': 'senate_drupal_newscontent', 'url_base': 'https://foushee.house.gov/media/press-releases'},
    'frost': {'method': 'senate_drupal_newscontent', 'url_base': 'https://frost.house.gov/media/press-releases'},
    'hoyle': {'method': 'senate_drupal_newscontent', 'url_base': 'https://hoyle.house.gov/media/press-releases'},
    'levin': {'method': 'senate_drupal_newscontent', 'url_base': 'https://levin.house.gov/media/press-releases'},
    'mcgarvey': {'method': 'senate_drupal_newscontent', 'url_base': 'https://mcgarvey.house.gov/media/press-releases'},
    'sarajacobs': {'method': 'senate_drupal_newscontent', 'url_base': 'https://sarajacobs.house.gov/news/press-releases'},
    'thanedar': {'method': 'senate_drupal_newscontent', 'url_base': 'https://thanedar.house.gov/media/press-releases'},
    'torres': {'method': 'senate_drupal_newscontent', 'url_base': 'https://torres.house.gov/media-center/press-releases'},
    'watsoncoleman': {'method': 'senate_drupal_newscontent', 'url_base': 'https://watsoncoleman.house.gov/newsroom/press-releases'},
    # Group 2: post-media-digest-item
    'austinscott': {'method': 'generic', 'url_base': 'https://austinscott.house.gov/press-releases', 'container': '.post-media-digest-item', 'title_sel': '.post-media-digest-title', 'link_sel': 'a.media-digest-body-link', 'date_sel': '.post-media-digest-date', 'date_fmt': ['%B %d, %Y', '%B %d'], 'pagination': '?page={page}'},
    'desjarlais': {'method': 'generic', 'url_base': 'https://desjarlais.house.gov/media-center', 'container': '.post-media-digest-item', 'title_sel': '.post-media-digest-title', 'link_sel': 'a.media-digest-body-link', 'date_sel': '.post-media-digest-date', 'date_fmt': ['%B %d, %Y', '%B %d'], 'pagination': '?page={page}'},
    'gooden': {'method': 'generic', 'url_base': 'https://gooden.house.gov/press-releases', 'container': '.post-media-digest-item', 'title_sel': '.post-media-digest-title', 'link_sel': 'a.media-digest-body-link', 'detail_date_sel': '.date', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'max_results': 10},
    'hayes': {'method': 'generic', 'url_base': 'https://hayes.house.gov/press-releases', 'container': '.post-media-digest-item', 'title_sel': '.post-media-digest-title', 'link_sel': 'a.media-digest-body-link', 'date_sel': '.post-media-digest-date', 'date_fmt': ['%B %d, %Y', '%B %d'], 'pagination': '?page={page}'},
    'himes': {'method': 'generic', 'url_base': 'https://himes.house.gov/statements-and-releases/', 'container': 'article.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/?et_blog'},
    # Group 3: WordPress/Divi .et_pb_post
    'clayhiggins': {'method': 'generic', 'url_base': 'https://clayhiggins.house.gov/category/press-releases/', 'container': '.et_pb_post', 'title_sel': 'h2.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'fulcher': {'method': 'generic', 'url_base': 'https://fulcher.house.gov/category/press-releases/', 'container': '.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'whitesides': {'method': 'generic', 'url_base': 'https://whitesides.house.gov/category/press-releases/', 'container': '.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    # Group 4: Unique templates
    'chrissmith': {'method': 'generic', 'url_base': 'https://chrissmith.house.gov/news/documentquery.aspx', 'container': 'ul.UnorderedNewsList li', 'title_sel': 'a.middleheadline', 'date_regex': r'on\s+(\w+ \d+,\s*\d{4})', 'date_fmt': ['%B %d, %Y'], 'pagination': '?Page={page}', 'url_prefix': '/news/'},
    'crane': {'method': 'generic', 'url_base': 'https://crane.house.gov/media/', 'container': '.item.post', 'title_sel': 'h3', 'link_sel': 'a.btn', 'date_sel': 'span.date', 'date_fmt': ['%B %d %Y', '%B %d, %Y'], 'pagination': 'page/{page}/'},
    'juliabrownley': {'method': 'generic', 'url_base': 'https://juliabrownley.house.gov/category/press-releases/', 'container': 'article.news-item', 'title_sel': 'h2', 'link_sel': 'a', 'date_sel': 'time', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},
    'kevinmullin': {'method': 'generic', 'url_base': 'https://kevinmullin.house.gov/category/press_release/', 'container': 'a.item', 'title_sel': 'span.title', 'date_sel': 'span.date', 'date_fmt': ['%B %d, %Y'], 'pagination': 'page/{page}/'},
    'strickland': {'method': 'generic', 'url_base': 'https://strickland.house.gov/category/press_release/', 'container': '.type-post', 'title_sel': '.wp-block-post-title a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%dT%H:%M:%S%z', '%b %d, %Y'], 'pagination': 'page/{page}/'},
    # Senate Elementor sites - jet_listing with h4
    'padilla': {'method': 'generic', 'url_base': 'https://www.padilla.senate.gov/newsroom/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h4 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    'warnock': {'method': 'generic', 'url_base': 'https://www.warnock.senate.gov/newsroom/press-releases/', 'container': '.jet-listing-grid__item', 'title_sel': 'h4 a', 'date_sel': 'span.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?jsf=jet-engine:press-list&pagenum={page}'},
    # Senate Elementor ArticleBlock with <a> container
    'sheehy': {'method': 'generic', 'url_base': 'https://www.sheehy.senate.gov/newsroom/press-releases/', 'container': 'a.ArticleBlock', 'title_sel': 'h4', 'date_sel': '.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'husted': {'method': 'generic', 'url_base': 'https://www.husted.senate.gov/newsroom/press-releases/', 'container': 'a.ArticleBlock', 'title_sel': 'h4', 'date_sel': '.elementor-icon-list-text', 'date_fmt': ['%m.%d.%y', '%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    # Senate Elementor ArticleBlock with div container, first <a> as title/link
    'alsobrooks': {'method': 'generic', 'url_base': 'https://www.alsobrooks.senate.gov/newsroom/press-releases/', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': '.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    'davemccormick': {'method': 'generic', 'url_base': 'https://www.mccormick.senate.gov/newsroom/press-releases/', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': '.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    # Senate Elementor ArticleBlock with div container, first <a> as title/link (schiff same pattern)
    'schiff': {'method': 'generic', 'url_base': 'https://www.schiff.senate.gov/newsroom/press-releases/', 'container': 'div.ArticleBlock', 'title_sel': 'a', 'date_sel': '.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    # Senate Elementor ArticleBlock with <a> container (bluntrochester same as sheehy/husted)
    'bluntrochester': {'method': 'generic', 'url_base': 'https://www.bluntrochester.senate.gov/newsroom/press-releases/', 'container': 'a.ArticleBlock', 'title_sel': 'h4', 'date_sel': '.elementor-icon-list-text', 'date_fmt': ['%B %d, %Y'], 'pagination': '?PageNum_rs={page}'},
    # Senate Elementor loop-grid sites
    'gallego': {'method': 'generic', 'url_base': 'https://www.gallego.senate.gov/newsroom/press-releases/', 'container': '.e-loop-item', 'title_sel': 'h3 a', 'date_sel': 'time', 'date_fmt': ['%B %d, %Y'], 'pagination': '?e-page-022ac3b={page}'},
    'banks': {'method': 'generic', 'url_base': 'https://www.banks.senate.gov/news/press-releases/', 'container': '.e-loop-item', 'title_sel': 'h3', 'date_sel': 'time', 'date_fmt': ['%A, %B %d, %Y', '%B %d, %Y'], 'pagination': '?e-page-2ba521a={page}'},
    # WordPress article-based senate sites
    'slotkin': {'method': 'generic', 'url_base': 'https://www.slotkin.senate.gov/newsroom/', 'container': 'article', 'title_sel': 'h3 a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y', '%B %d, %Y'], 'pagination': 'page/{page}/'},
    # Senate Drupal newscontent
    'warren': {'method': 'senate_drupal_newscontent', 'url_base': 'https://www.warren.senate.gov/newsroom/press-releases'},
    # WordPress/Divi .et_pb_post (neal)
    'neal': {'method': 'generic', 'url_base': 'https://neal.house.gov/category/press-releases/', 'container': '.et_pb_post', 'title_sel': 'h3.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},

    # article_block pattern - Senate sites with .ArticleBlock and h3 titles
    'booker': {'method': 'article_block', 'url_base': 'https://www.booker.senate.gov/news/press'},
    'cramer': {'method': 'article_block', 'url_base': 'https://www.cramer.senate.gov/news/press-releases'},

    # article_block_h2_date pattern - Senate sites with .ArticleBlock and h2 titles
    'blumenthal': {'method': 'article_block_h2_date', 'url_base': 'https://www.blumenthal.senate.gov/newsroom/press'},
    'collins': {'method': 'article_block_h2_date', 'url_base': 'https://www.collins.senate.gov/newsroom/press-releases'},

    # article_newsblocker pattern - House documentquery sites with article elements
    'balderson': {'method': 'article_newsblocker', 'url_base': 'https://balderson.house.gov/news/documentquery.aspx?DocumentTypeID=27'},
    'case': {'method': 'article_newsblocker', 'url_base': 'https://case.house.gov/news/documentquery.aspx?DocumentTypeID=27'},

    # article_span_published pattern - sites with article and span.published
    'hickenlooper': {'method': 'article_span_published', 'url_base': 'https://www.hickenlooper.senate.gov/press/page/'},

    # document_query_new pattern - House documentquery with h2 a title (converted to generic)
    'wassermanschultz': {'method': 'generic', 'url_base': 'https://wassermanschultz.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'hern': {'method': 'generic', 'url_base': 'https://hern.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},
    'fletcher': {'method': 'generic', 'url_base': 'https://fletcher.house.gov/news/documentquery.aspx', 'container': 'article', 'title_sel': 'h2 a', 'date_sel': 'time', 'date_attr': 'datetime', 'date_fmt': ['%Y-%m-%d'], 'pagination': '?DocumentTypeID=27&Page={page}', 'url_prefix': '/news/'},

    # elementor_post_date pattern - WordPress/Elementor with .elementor-post-date
    'sanders': {'method': 'elementor_post_date', 'url_base': 'https://www.sanders.senate.gov/media/press-releases/'},

    # jetlisting_h2 pattern - JetEngine listing grid with h2 titles
    'ricketts': {'method': 'jetlisting_h2', 'url_base': 'https://www.ricketts.senate.gov/newsroom/press-releases/?jsf=jet-engine:press-list&pagenum='},

    # recordlist pattern - House sites with table.recordList
    'fitzpatrick': {'method': 'table_recordlist_date', 'url_base': 'https://fitzpatrick.house.gov/press-releases'},

    # senate_drupal pattern - Senate Drupal sites with #newscontent
    'murkowski': {'method': 'senate_drupal', 'url_base': 'https://www.murkowski.senate.gov/press/press-releases'},
    'sullivan': {'method': 'senate_drupal', 'url_base': 'https://www.sullivan.senate.gov/newsroom/press-releases'},

    # senate_drupal_newscontent pattern - House/Senate sites with #newscontent
    'huffman': {'method': 'senate_drupal_newscontent', 'url_base': 'https://huffman.house.gov/media-center/press-releases'},
    'castro': {'method': 'senate_drupal_newscontent', 'url_base': 'https://castro.house.gov/media-center/press-releases'},
    'ansari': {'method': 'senate_drupal_newscontent', 'url_base': 'https://ansari.house.gov/media/press-releases'},

    # tokuda - similar to senate_drupal_newscontent but uses #press
    'tokuda': {'method': 'tokuda', 'url_base': 'https://tokuda.house.gov/media/press-releases'},

    # react pattern - Next.js/React sites with __NEXT_DATA__ JSON
    'nikemawilliams': {'method': 'react', 'url_base': 'https://nikemawilliams.house.gov/press'},
    'kiley': {'method': 'react', 'url_base': 'https://kiley.house.gov/press'},
    'yakym': {'method': 'react', 'url_base': 'https://yakym.house.gov/press'},
    'ritchietorres': {'method': 'react', 'url_base': 'https://ritchietorres.house.gov/press'},
    'cloud': {'method': 'react', 'url_base': 'https://cloud.house.gov/press'},
    'owens': {'method': 'react', 'url_base': 'https://owens.house.gov/press'},
    'budzinski': {'method': 'react', 'url_base': 'https://budzinski.house.gov/press'},
    'gluesenkampperez': {'method': 'react', 'url_base': 'https://gluesenkampperez.house.gov/press'},
    'landsman': {'method': 'react', 'url_base': 'https://landsman.house.gov/press'},
    'moskowitz': {'method': 'react', 'url_base': 'https://moskowitz.house.gov/press'},
    'gottheimer': {'method': 'react', 'url_base': 'https://gottheimer.house.gov/press'},
    'kiggans': {'method': 'rss', 'url_base': 'https://kiggans.house.gov/feed/'},
    'luna': {'method': 'react', 'url_base': 'https://luna.house.gov/press'},
    'maxmiller': {'method': 'react', 'url_base': 'https://maxmiller.house.gov/press'},

    # cornyn - AJAX/JSON endpoint
    'cornyn': {'method': 'cornyn', 'url_base': 'https://www.cornyn.senate.gov/news/'},

    # fischer - Senate table-based
    'fischer': {'method': 'table_recordlist_date', 'url_base': 'https://www.fischer.senate.gov/public/index.cfm/press-releases'},

    'clark': {'method': 'generic', 'url_base': 'https://katherineclark.house.gov/newsroom/', 'container': 'article.et_pb_post', 'title_sel': '.entry-title a', 'date_sel': 'span.published', 'date_fmt': ['%b %d, %Y'], 'pagination': 'page/{page}/'},

    # joyce - React/Next.js (same as react pattern)
    'joyce': {'method': 'joyce', 'url_base': 'https://joyce.house.gov/press'},

    # New members (2026) - media_body pattern
    'fuller': {'method': 'generic', 'url_base': 'https://fuller.house.gov/media/press-releases', 'container': '.media-body', 'title_sel': 'a', 'date_sel': '.row .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
    'mejia': {'method': 'generic', 'url_base': 'https://mejia.house.gov/media/press-releases', 'container': '.media-body', 'title_sel': 'a', 'date_sel': '.row .col-auto', 'date_fmt': ['%B %d, %Y'], 'pagination': '?page={page}', 'page_offset': -1},
}

VALID_METHODS = {
    'generic', 'rss', 'media_body', 'article_block_h2_p_date',
    'jet_listing_elementor', 'table_recordlist_date',
    'element_post_media', 'senate_drupal_newscontent',
    'article_block', 'article_block_h2_date', 'article_newsblocker',
    'article_span_published', 'document_query_new', 'elementor_post_date',
    'jetlisting_h2', 'senate_drupal', 'react',
    'tokuda', 'cornyn', 'joyce',
}

VALID_GENERIC_KEYS = {
    'method', 'url_base', 'container', 'title_sel', 'date_sel',
    'date_fmt', 'date_attr', 'date_from_next_sibling', 'date_sel_join',
    'pagination', 'url_prefix', 'skip_first', 'link_sel', 'link_attr',
    'base_domain', 'max_results', 'page_offset', 'date_regex',
    'detail_date_sel', 'detail_date_attr', 'detail_date_fmt',
}

VALID_BATCH_KEYS = {'method', 'url_base'}


def validate_config():
    """Validate all SCRAPER_CONFIG entries at import time."""
    for name, config in SCRAPER_CONFIG.items():
        # All entries must have method and url_base
        if 'method' not in config:
            raise ValueError(f"Scraper '{name}': missing required key 'method'")
        if 'url_base' not in config:
            raise ValueError(f"Scraper '{name}': missing required key 'url_base'")

        method = config['method']
        if method not in VALID_METHODS:
            raise ValueError(
                f"Scraper '{name}': unknown method '{method}'. "
                f"Valid methods: {sorted(VALID_METHODS)}"
            )

        if method == 'generic':
            # Generic entries need container and title_sel
            if 'container' not in config:
                raise ValueError(f"Scraper '{name}': generic method requires 'container'")
            if 'title_sel' not in config:
                raise ValueError(f"Scraper '{name}': generic method requires 'title_sel'")

            # Check for unknown keys (catches typos)
            unknown = set(config.keys()) - VALID_GENERIC_KEYS
            if unknown:
                raise ValueError(
                    f"Scraper '{name}': unknown config keys {unknown}. "
                    f"Valid keys: {sorted(VALID_GENERIC_KEYS)}"
                )

            # date_fmt must be a list
            if 'date_fmt' in config and not isinstance(config['date_fmt'], list):
                raise ValueError(
                    f"Scraper '{name}': 'date_fmt' must be a list, "
                    f"got {type(config['date_fmt']).__name__}"
                )
        else:
            # Batch method entries should only have method and url_base
            unknown = set(config.keys()) - VALID_BATCH_KEYS
            if unknown:
                raise ValueError(
                    f"Scraper '{name}': batch method '{method}' only accepts "
                    f"'method' and 'url_base', got extra keys {unknown}"
                )


validate_config()

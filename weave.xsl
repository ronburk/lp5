<?xml version="1.0" encoding="UTF-8"?>
<!--
     weave.xsl - make one XML snapshot of all discovered lp5 articles.

     Examples (run from the repository root through the lp5 CLI):
       ./lp5 weave
       ./lp5 -w alternate.xml weave

     The result is an index for source-navigation tools, not tangled output.
     Each article is emitted in preorder, with the root article first. Article
     IDs are filenames, and code sections are grouped by bundle name so
     callers can find each bundle.
     A keyword-index maps canonical keywords to distinct article filenames.
     Canonicalization applies normalize-space() and ASCII A-Z to a-z folding;
     other characters, including Unicode case, are preserved.
     Code text and lp5-* reference
     elements retain their original order and content.

     The input file is the root article. Its directory is the base for
     document() lookups and is passed to my:ls() for directory enumeration.
     The root article is emitted first. Afterwards numeric article filenames
     are considered in ascending numeric order, followed by nonnumeric
     article filenames in ascending text order. Only files are considered.

     Article validation is imported from tangle.xsl so both transforms apply
     the same on-disk format rules to each article that exists. Missing child
     articles remain explicit unresolved links in the index. Articles not
     reachable from the root are appended as orphan trees; their child links
     determine preorder within each orphan tree. Each tree root has no parent
     attribute. Cycles and multiple parents are rejected.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:my="http://example.com/lp5ext"
    xmlns:exsl="http://exslt.org/common"
    exclude-result-prefixes="my"
    extension-element-prefixes="exsl">

    <!-- Reuse the shared article validator and path helper from the tangle. -->
    <xsl:import href="tangle.xsl"/>

    <!-- Override tangle.xsl's HTML output method for this XML result. -->
    <!-- Do not pretty-print: serializer-inserted whitespace could alter code. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <!-- lp5.c passes the directory containing the input root article. -->
    <xsl:param name="source-directory" select="'lp5.lp5'"/>

    <!-- The rooted match excludes similarly named markup in explanations. -->
    <xsl:key name="weave-keywords-by-value" match="/articles/article/keywords/li"
        use="translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>

    <xsl:template match="/">
        <xsl:variable name="source-root" select="/"/>
        <xsl:variable name="directory-entries"
            select="my:ls($source-directory)[@type='file']"/>

        <!-- List files, preserving numeric order and ordering other articles by name. -->
        <xsl:variable name="disk-files">
            <files>
                <xsl:for-each select="$directory-entries[
                        string-length(@name) &gt; 4 and
                        substring(@name, string-length(@name) - 3) = '.lp5' and
                        substring-after(@name, '.lp5') = '' and
                        string-length(substring-before(@name, '.lp5')) &gt; 0 and
                        translate(substring-before(@name, '.lp5'), '0123456789', '') = '']">
                    <xsl:sort select="number(substring-before(@name, '.lp5'))"
                              data-type="number" order="ascending"/>
                    <xsl:sort select="@name" data-type="text" order="ascending"/>
                    <file name="{@name}"/>
                </xsl:for-each>
                <xsl:for-each select="$directory-entries[
                        string-length(@name) &gt; 4 and
                        substring(@name, string-length(@name) - 3) = '.lp5' and
                        substring-after(@name, '.lp5') = '' and
                        string-length(substring-before(@name, '.lp5')) &gt; 0 and
                        translate(substring-before(@name, '.lp5'), '0123456789', '') != '']">
                    <xsl:sort select="@name" data-type="text" order="ascending"/>
                    <file name="{@name}"/>
                </xsl:for-each>
            </files>
        </xsl:variable>

        <!-- Build the available-article graph. Missing links are not graph edges. -->
        <xsl:variable name="article-graph">
            <graph>
                <xsl:for-each select="exsl:node-set($disk-files)/files/file">
                    <xsl:variable name="file" select="string(@name)"/>
                    <xsl:variable name="article" select="document($file, $source-root)"/>
                    <xsl:if test="$article/*">
                        <xsl:call-template name="validate-article">
                            <xsl:with-param name="document" select="$article"/>
                            <xsl:with-param name="location" select="$file"/>
                        </xsl:call-template>
                        <article file="{$file}">
                            <xsl:for-each select="$article/template/children/li">
                                <xsl:variable name="child-file" select="string(@id)"/>
                                <xsl:if test="$directory-entries[@name = $child-file]">
                                    <child file="{$child-file}"/>
                                </xsl:if>
                            </xsl:for-each>
                        </article>
                    </xsl:if>
                </xsl:for-each>
            </graph>
        </xsl:variable>
        <xsl:variable name="graph" select="exsl:node-set($article-graph)/graph"/>

        <!-- The root cannot have a parent; no available article can have two. -->
        <xsl:for-each select="$graph/article">
            <xsl:variable name="file" select="string(@file)"/>
            <xsl:variable name="incoming" select="$graph/article/child[@file = $file]"/>
            <xsl:if test="$file = 'lp5.lp5' and $incoming">
                <xsl:message terminate="yes">weave: root article 'lp5.lp5' has incoming parent link(s): <xsl:for-each select="$incoming"><xsl:if test="position() &gt; 1">, </xsl:if>'<xsl:value-of select="../@file"/>'</xsl:for-each>.</xsl:message>
            </xsl:if>
            <xsl:if test="count($incoming) &gt; 1">
                <xsl:message terminate="yes">weave: article '<xsl:value-of select="$file"/>' has multiple parent links from <xsl:for-each select="$incoming"><xsl:if test="position() &gt; 1">, </xsl:if>'<xsl:value-of select="../@file"/>'</xsl:for-each>.</xsl:message>
            </xsl:if>
            <xsl:if test="child[@file = $file]">
                <xsl:message terminate="yes">weave: article '<xsl:value-of select="$file"/>' links to itself.</xsl:message>
            </xsl:if>
        </xsl:for-each>

        <!-- Visit the root tree first and carry one global set of visited files. -->
        <xsl:variable name="root-result">
            <xsl:call-template name="visit-article">
                <xsl:with-param name="document" select="."/>
                <xsl:with-param name="source-root" select="$source-root"/>
                <xsl:with-param name="available-files" select="$directory-entries"/>
                <xsl:with-param name="location" select="'lp5.lp5'"/>
                <xsl:with-param name="seen" select="'|'"/>
            </xsl:call-template>
        </xsl:variable>
        <xsl:variable name="root-seen"
            select="string(exsl:node-set($root-result)/result/@seen)"/>

        <!-- Orphan roots have no incoming link from any available article. -->
        <xsl:variable name="orphan-roots">
            <roots>
                <xsl:for-each select="$graph/article[@file != 'lp5.lp5']">
                    <xsl:variable name="file" select="string(@file)"/>
                    <xsl:if test="not($graph/article/child[@file = $file])">
                        <orphan file="{$file}"/>
                    </xsl:if>
                </xsl:for-each>
            </roots>
        </xsl:variable>

        <!-- Emit orphan roots in discovery order, following each children list. -->
        <xsl:variable name="orphan-root-result">
            <xsl:call-template name="visit-article-list">
                <xsl:with-param name="articles" select="exsl:node-set($orphan-roots)/roots/orphan"/>
                <xsl:with-param name="source-root" select="$source-root"/>
                <xsl:with-param name="available-files" select="$directory-entries"/>
                <xsl:with-param name="seen" select="$root-seen"/>
            </xsl:call-template>
        </xsl:variable>

        <!-- Any undiscovered available articles have no forest root: they cycle. -->
        <xsl:variable name="all-seen"
            select="string(exsl:node-set($orphan-root-result)/result/@seen)"/>
        <xsl:for-each select="$graph/article[not(contains($all-seen, concat('|', @file, '|')))]">
            <xsl:variable name="file" select="string(@file)"/>
            <xsl:variable name="incoming" select="$graph/article/child[@file = $file]"/>
            <xsl:message terminate="yes">weave: cycle includes article '<xsl:value-of select="$file"/>'<xsl:if test="$incoming"> (incoming link from '<xsl:value-of select="$incoming[1]/../@file"/>')</xsl:if>.</xsl:message>
        </xsl:for-each>

        <!-- This one preorder supplies the article list and both indexes. -->
        <xsl:variable name="article-records">
            <articles>
                <xsl:for-each select="exsl:node-set($root-result)/result/article">
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="."/>
                </xsl:for-each>
                <xsl:for-each select="exsl:node-set($orphan-root-result)/result/article">
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="."/>
                </xsl:for-each>
                <xsl:text>&#10;  </xsl:text>
            </articles>
        </xsl:variable>

        <lp5-weave version="1">
            <!-- Article order is preorder, so the first article is the root. -->
            <xsl:text>&#10;  </xsl:text>
            <xsl:copy-of select="exsl:node-set($article-records)/articles"/>

            <!-- Build a lookup list from bundle names to their code sections. -->
            <xsl:text>&#10;  </xsl:text>
            <bundles>
                <!-- EXSLT node-set lets XSLT 1.0 group the emitted records. -->
                <xsl:for-each select="exsl:node-set($article-records)/articles/article/section[@data-lp5-kind='code']">
                    <xsl:variable name="bundle-name" select="normalize-space(name)"/>
                    <xsl:if test="not(preceding::section[@data-lp5-kind='code'][normalize-space(name) = $bundle-name])">
                        <xsl:text>&#10;    </xsl:text>
                        <bundle name="{$bundle-name}">
                            <xsl:for-each select="exsl:node-set($article-records)/articles/article/section[@data-lp5-kind='code'][normalize-space(name) = $bundle-name]">
                                <xsl:text>&#10;      </xsl:text>
                                <section article="{../@file}"/>
                            </xsl:for-each>
                            <xsl:text>&#10;    </xsl:text>
                        </bundle>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>&#10;  </xsl:text>
            </bundles>

            <xsl:text>&#10;  </xsl:text>
            <keyword-index>
                <xsl:for-each select="exsl:node-set($article-records)/articles/article/keywords/li[normalize-space(.) != '']">
                    <xsl:sort select="translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
                              data-type="text" order="ascending"/>
                    <xsl:variable name="value"
                        select="translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
                    <!-- key() uses the temporary article-records document. -->
                    <xsl:if test="generate-id() = generate-id(key('weave-keywords-by-value', $value)[1])">
                        <xsl:text>&#10;    </xsl:text>
                        <keyword value="{$value}">
                            <!-- The parent path deduplicates articles and retains weave order. -->
                            <xsl:for-each select="key('weave-keywords-by-value', $value)/../..">
                                <xsl:text>&#10;      </xsl:text>
                                <article file="{@file}"/>
                            </xsl:for-each>
                            <xsl:text>&#10;    </xsl:text>
                        </keyword>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>&#10;  </xsl:text>
            </keyword-index>
            <xsl:text>&#10;</xsl:text>
        </lp5-weave>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

    <!-- Visit one article and its descendants, threading a global seen list. -->
    <xsl:template name="visit-article">
        <xsl:param name="document"/>
        <xsl:param name="source-root"/>
        <xsl:param name="available-files"/>
        <xsl:param name="location"/>
        <xsl:param name="seen"/>
        <xsl:param name="parent-file" select="''"/>

        <xsl:choose>
            <xsl:when test="not($document/*) or contains($seen, concat('|', $location, '|'))">
                <result seen="{$seen}"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:call-template name="validate-article">
                    <xsl:with-param name="document" select="$document"/>
                    <xsl:with-param name="location" select="$location"/>
                </xsl:call-template>
                <xsl:variable name="seen-current" select="concat($seen, $location, '|')"/>
                <xsl:variable name="descendants">
                    <xsl:call-template name="visit-child-links">
                        <xsl:with-param name="links" select="$document/template/children/li"/>
                        <xsl:with-param name="source-root" select="$source-root"/>
                        <xsl:with-param name="available-files" select="$available-files"/>
                        <xsl:with-param name="seen" select="$seen-current"/>
                        <xsl:with-param name="parent-file" select="$location"/>
                    </xsl:call-template>
                </xsl:variable>
                <result seen="{string(exsl:node-set($descendants)/result/@seen)}">
                    <article file="{$location}">
                        <xsl:if test="$parent-file != ''">
                            <xsl:attribute name="parent"><xsl:value-of select="$parent-file"/></xsl:attribute>
                        </xsl:if>
                        <!-- Preserve source order and section content. -->
                        <xsl:for-each select="$document/template/heading |
                                $document/template/keywords |
                                $document/template/section[@data-lp5-kind='explanation'] |
                                $document/template/section[@data-lp5-kind='code']">
                            <xsl:text>&#10;      </xsl:text>
                            <xsl:copy-of select="."/>
                        </xsl:for-each>

                        <!-- Child IDs are filenames relative to this article. -->
                        <xsl:text>&#10;      </xsl:text>
                        <children>
                            <xsl:for-each select="$document/template/children/li">
                                <xsl:variable name="child-filename" select="string(@id)"/>
                                <xsl:text>&#10;        </xsl:text>
                                <child>
                                    <xsl:attribute name="file"><xsl:value-of select="$child-filename"/></xsl:attribute>
                                    <xsl:attribute name="status">
                                        <xsl:choose>
                                            <xsl:when test="$available-files[@name = $child-filename]">
                                                <xsl:variable name="child-document"
                                                    select="document($child-filename, .)"/>
                                                <xsl:choose>
                                                    <xsl:when test="$child-document/*">available</xsl:when>
                                                    <xsl:otherwise>missing</xsl:otherwise>
                                                </xsl:choose>
                                            </xsl:when>
                                            <xsl:otherwise>missing</xsl:otherwise>
                                        </xsl:choose>
                                    </xsl:attribute>
                                </child>
                            </xsl:for-each>
                            <xsl:if test="$document/template/children/li">
                                <xsl:text>&#10;      </xsl:text>
                            </xsl:if>
                        </children>
                        <xsl:text>&#10;    </xsl:text>
                    </article>
                    <xsl:copy-of select="exsl:node-set($descendants)/result/article"/>
                </result>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Visit child links sequentially so each call sees previous visits. -->
    <xsl:template name="visit-child-links">
        <xsl:param name="links"/>
        <xsl:param name="source-root"/>
        <xsl:param name="available-files"/>
        <xsl:param name="seen"/>
        <xsl:param name="parent-file"/>

        <xsl:choose>
            <xsl:when test="not($links)">
                <result seen="{$seen}"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:variable name="child-filename" select="string($links[1]/@id)"/>
                <xsl:variable name="first">
                    <xsl:choose>
                        <xsl:when test="$available-files[@name = $child-filename]">
                            <xsl:variable name="child-document"
                                select="document($child-filename, $links[1])"/>
                            <xsl:choose>
                                <xsl:when test="$child-document/*">
                                    <xsl:call-template name="visit-article">
                                        <xsl:with-param name="document" select="$child-document"/>
                                        <xsl:with-param name="source-root" select="$source-root"/>
                                        <xsl:with-param name="available-files" select="$available-files"/>
                                        <xsl:with-param name="location" select="$child-filename"/>
                                        <xsl:with-param name="seen" select="$seen"/>
                                        <xsl:with-param name="parent-file" select="$parent-file"/>
                                    </xsl:call-template>
                                </xsl:when>
                                <xsl:otherwise>
                                    <xsl:message>
                                        <xsl:text>Warning: article '</xsl:text>
                                        <xsl:value-of select="$child-filename"/>
                                        <xsl:text>' is linked but unavailable.</xsl:text>
                                    </xsl:message>
                                    <result seen="{$seen}"/>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:when>
                        <xsl:otherwise>
                            <xsl:message>
                                <xsl:text>Warning: article '</xsl:text>
                                <xsl:value-of select="$child-filename"/>
                                <xsl:text>' is linked but unavailable.</xsl:text>
                            </xsl:message>
                            <result seen="{$seen}"/>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:variable>
                <xsl:variable name="rest">
                    <xsl:call-template name="visit-child-links">
                        <xsl:with-param name="links" select="$links[position() &gt; 1]"/>
                        <xsl:with-param name="source-root" select="$source-root"/>
                        <xsl:with-param name="available-files" select="$available-files"/>
                        <xsl:with-param name="seen"
                            select="string(exsl:node-set($first)/result/@seen)"/>
                        <xsl:with-param name="parent-file" select="$parent-file"/>
                    </xsl:call-template>
                </xsl:variable>
                <result seen="{string(exsl:node-set($rest)/result/@seen)}">
                    <xsl:copy-of select="exsl:node-set($first)/result/article"/>
                    <xsl:copy-of select="exsl:node-set($rest)/result/article"/>
                </result>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Visit candidate roots in list order, threading the global seen list. -->
    <xsl:template name="visit-article-list">
        <xsl:param name="articles"/>
        <xsl:param name="source-root"/>
        <xsl:param name="available-files"/>
        <xsl:param name="seen"/>

        <xsl:choose>
            <xsl:when test="not($articles)">
                <result seen="{$seen}"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:variable name="filename" select="string($articles[1]/@file)"/>
                <xsl:variable name="document" select="document($filename, $source-root)"/>
                <xsl:variable name="first">
                    <xsl:call-template name="visit-article">
                        <xsl:with-param name="document" select="$document"/>
                        <xsl:with-param name="source-root" select="$source-root"/>
                        <xsl:with-param name="available-files" select="$available-files"/>
                        <xsl:with-param name="location" select="$filename"/>
                        <xsl:with-param name="seen" select="$seen"/>
                    </xsl:call-template>
                </xsl:variable>
                <xsl:variable name="rest">
                    <xsl:call-template name="visit-article-list">
                        <xsl:with-param name="articles" select="$articles[position() &gt; 1]"/>
                        <xsl:with-param name="source-root" select="$source-root"/>
                        <xsl:with-param name="available-files" select="$available-files"/>
                        <xsl:with-param name="seen"
                            select="string(exsl:node-set($first)/result/@seen)"/>
                    </xsl:call-template>
                </xsl:variable>
                <result seen="{string(exsl:node-set($rest)/result/@seen)}">
                    <xsl:copy-of select="exsl:node-set($first)/result/article"/>
                    <xsl:copy-of select="exsl:node-set($rest)/result/article"/>
                </result>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>


</xsl:stylesheet>

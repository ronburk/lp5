<?xml version="1.0" encoding="UTF-8"?>
<!--
     weave.xsl - make one XML snapshot of all discovered lp5 articles.

     Example (run from the repository root through the lp5 CLI):
       ./lp5 weave -o weave.xml

     The result is an index for source-navigation tools, not tangled output.
     Each article is emitted in preorder, with the root article first. Article
     IDs are filenames, and code sections are grouped by bundle name so
     callers can find each bundle.
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
     reachable from the root are appended as orphans; their child links
     determine preorder within each orphan tree. A component with no root
     (for example, a cycle) starts at its first still-unseen file in discovery
     order.
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

        <!-- Build a temporary graph of discovered articles outside the root tree. -->
        <xsl:variable name="orphan-candidates">
            <orphans>
                <xsl:for-each select="exsl:node-set($disk-files)/files/file">
                    <xsl:variable name="file" select="string(@name)"/>
                    <xsl:if test="not(contains($root-seen, concat('|', $file, '|')))">
                        <xsl:variable name="article" select="document($file, $source-root)"/>
                        <orphan file="{$file}">
                            <xsl:for-each select="$article/template/children/li">
                                <child file="{@id}"/>
                            </xsl:for-each>
                        </orphan>
                    </xsl:if>
                </xsl:for-each>
            </orphans>
        </xsl:variable>

        <!-- Orphan roots have no incoming child link from another orphan. -->
        <xsl:variable name="orphan-roots">
            <roots>
                <xsl:for-each select="exsl:node-set($orphan-candidates)/orphans/orphan">
                    <xsl:variable name="file" select="string(@file)"/>
                    <xsl:if test="not(exsl:node-set($orphan-candidates)/orphans/orphan/child[@file = $file])">
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

        <!-- Visit any leftovers to include components with no root, such as cycles. -->
        <xsl:variable name="orphan-fallback-result">
            <xsl:call-template name="visit-article-list">
                <xsl:with-param name="articles" select="exsl:node-set($orphan-candidates)/orphans/orphan"/>
                <xsl:with-param name="source-root" select="$source-root"/>
                <xsl:with-param name="available-files" select="$directory-entries"/>
                <xsl:with-param name="seen"
                    select="string(exsl:node-set($orphan-root-result)/result/@seen)"/>
            </xsl:call-template>
        </xsl:variable>

        <!-- This one preorder supplies both the article list and bundle index. -->
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
                <xsl:for-each select="exsl:node-set($orphan-fallback-result)/result/article">
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
                    </xsl:call-template>
                </xsl:variable>
                <result seen="{string(exsl:node-set($descendants)/result/@seen)}">
                    <article file="{$location}">
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

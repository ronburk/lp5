<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:output method="html" encoding="UTF-8" omit-xml-declaration="yes"/>

    <!-- XPath 1.0 cannot distinguish CDATA sections from ordinary text nodes;
         the validator can check the XML tree shape, not the lexical CDATA form. -->

    <!-- Pass the root article's path for file paths in script warnings. -->
    <xsl:param name="root-location" select="'input article'"/>

    <xsl:template match="/">
        <xsl:call-template name="validate-article-tree">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="location" select="$root-location"/>
            <xsl:with-param name="visited" select="'|'"/>
        </xsl:call-template>
        <xsl:call-template name="emit-document">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="root" select="."/>
        </xsl:call-template>
        <xsl:call-template name="warn-about-scripts">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="location" select="$root-location"/>
            <xsl:with-param name="visited" select="'|'"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="validate-article-tree">
        <xsl:param name="document"/>
        <xsl:param name="location"/>
        <xsl:param name="visited"/>

        <xsl:variable name="document-id" select="generate-id($document)"/>
        <xsl:if test="not(contains($visited, concat('|', $document-id, '|')))">
            <xsl:call-template name="validate-article">
                <xsl:with-param name="document" select="$document"/>
                <xsl:with-param name="location" select="$location"/>
            </xsl:call-template>

            <xsl:for-each select="$document/template/children/li">
                <xsl:variable name="article-directory">
                    <xsl:call-template name="article-directory">
                        <xsl:with-param name="path" select="$location"/>
                    </xsl:call-template>
                </xsl:variable>
                <xsl:variable name="child-location">
                    <xsl:if test="string-length(string($article-directory))">
                        <xsl:value-of select="$article-directory"/>
                        <xsl:text>/</xsl:text>
                    </xsl:if>
                    <xsl:value-of select="@id"/>
                </xsl:variable>
                <xsl:variable name="child" select="document(string(@id), .)"/>
                <xsl:choose>
                    <xsl:when test="$child/*">
                        <xsl:call-template name="validate-article-tree">
                            <xsl:with-param name="document" select="$child"/>
                            <xsl:with-param name="location" select="string($child-location)"/>
                            <xsl:with-param name="visited"
                                select="concat($visited, $document-id, '|')"/>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:message>
                            <xsl:text>Warning: linked article '</xsl:text>
                            <xsl:value-of select="$child-location"/>
                            <xsl:text>' is unavailable; skipping it.</xsl:text>
                        </xsl:message>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:for-each>
        </xsl:if>
    </xsl:template>

    <xsl:template name="validate-article">
        <xsl:param name="document"/>
        <xsl:param name="location"/>

        <xsl:if test="count($document/*) != 1 or count($document/template) != 1">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': XML document root must be &lt;template&gt;.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="$document/template/*[not(self::children or self::heading or self::section)]">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': unexpected direct child &lt;</xsl:text>
                <xsl:value-of select="name($document/template/*[not(self::children or
                        self::heading or self::section)][1])"/>
                <xsl:text>&gt; of &lt;template&gt;.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="$document/template/text()[normalize-space()]">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': non-whitespace text is not allowed directly inside &lt;template&gt;.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="count($document/template/children) &gt; 1 or
                count($document/template/heading) &gt; 1 or
                count($document/template/section[@data-lp5-kind = 'explanation']) &gt; 1 or
                count($document/template/section[@data-lp5-kind = 'code']) &gt; 1">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': each permitted direct child of &lt;template&gt; may appear at most once.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="$document/template/section[not(@data-lp5-kind = 'explanation' or
                @data-lp5-kind = 'code')]">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': &lt;section&gt; must have data-lp5-kind="explanation" or "code".</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="$document/template/children/*[not(self::li)] or
                $document/template/children/text()[normalize-space()] or
                $document/template/children/li[not(@id) or
                    count(@*) != 1 or
                    string-length(@id) &lt;= 4 or
                    substring(@id, string-length(@id) - 3) != '.lp5' or
                    * or normalize-space(text())]">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': &lt;children&gt; must contain only empty &lt;li id="name.lp5"&gt; links.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="$document/template/section[@data-lp5-kind = 'code'] and
                (count($document/template/section[@data-lp5-kind = 'code']/name) != 1 or
                 count($document/template/section[@data-lp5-kind = 'code']/code) != 1 or
                 $document/template/section[@data-lp5-kind = 'code']/text()[normalize-space()] or
                 $document/template/section[@data-lp5-kind = 'code']/*[not(self::name or self::code)])">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': code section must contain exactly one &lt;name&gt; and one &lt;code&gt;.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:if test="$document/template/section[@data-lp5-kind = 'code']/code/node()[self::*[not(starts-with(name(), 'lp5-'))] or self::comment() or self::processing-instruction()]">
            <xsl:message terminate="yes">
                <xsl:text>Invalid article '</xsl:text>
                <xsl:value-of select="$location"/>
                <xsl:text>': children of &lt;code&gt; must be text or elements whose names start with "lp5-".</xsl:text>
            </xsl:message>
        </xsl:if>
    </xsl:template>

    <xsl:template name="warn-about-scripts">
        <xsl:param name="document"/>
        <xsl:param name="location"/>
        <xsl:param name="visited"/>

        <xsl:variable name="document-id" select="generate-id($document)"/>
        <xsl:if test="not(contains($visited, concat('|', $document-id, '|')))">
            <xsl:for-each select="$document//script">
                <xsl:message>
                    <xsl:text>Warning: found &lt;script&gt; element in article '</xsl:text>
                    <xsl:value-of select="$location"/>
                    <xsl:text>'. xsltproc may not parse script contents as intended.</xsl:text>
                </xsl:message>
            </xsl:for-each>

            <xsl:for-each select="$document/template/children/li">
                <xsl:variable name="article-directory">
                    <xsl:call-template name="article-directory">
                        <xsl:with-param name="path" select="$location"/>
                    </xsl:call-template>
                </xsl:variable>
                <xsl:variable name="child-location">
                    <xsl:if test="string-length(string($article-directory))">
                        <xsl:value-of select="$article-directory"/>
                        <xsl:text>/</xsl:text>
                    </xsl:if>
                    <xsl:value-of select="@id"/>
                </xsl:variable>
                <xsl:variable name="child" select="document(string(@id), .)"/>
                <xsl:call-template name="warn-about-scripts">
                    <xsl:with-param name="document" select="$child"/>
                    <xsl:with-param name="location" select="string($child-location)"/>
                    <xsl:with-param name="visited"
                        select="concat($visited, $document-id, '|')"/>
                </xsl:call-template>
            </xsl:for-each>
        </xsl:if>
    </xsl:template>

    <xsl:template name="article-directory">
        <xsl:param name="path"/>

        <xsl:if test="contains($path, '/')">
            <xsl:variable name="after-first-slash" select="substring-after($path, '/')"/>
            <xsl:choose>
                <xsl:when test="contains($after-first-slash, '/')">
                    <xsl:value-of select="substring-before($path, '/')"/>
                    <xsl:text>/</xsl:text>
                    <xsl:call-template name="article-directory">
                        <xsl:with-param name="path" select="$after-first-slash"/>
                    </xsl:call-template>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="substring-before($path, '/')"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:if>
    </xsl:template>

    <xsl:template name="emit-document">
        <xsl:param name="document"/>
        <xsl:param name="root"/>

        <xsl:for-each select="$document/template/section[@data-lp5-kind = 'code'][not(normalize-space(name))]/code">
            <xsl:apply-templates select="node()" mode="emit-code">
                <xsl:with-param name="root" select="$root"/>
                <xsl:with-param name="stack" select="'|'"/>
            </xsl:apply-templates>
        </xsl:for-each>

        <xsl:for-each select="$document/template/children/li">
            <xsl:variable name="child" select="document(string(@id), .)"/>
            <xsl:call-template name="emit-document">
                <xsl:with-param name="document" select="$child"/>
                <xsl:with-param name="root" select="$root"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>

    <xsl:template match="text()" mode="emit-code">
        <xsl:if test="not(parent::code and not(normalize-space(.)) and ../*)">
            <xsl:value-of select="." disable-output-escaping="yes"/>
        </xsl:if>
    </xsl:template>

    <xsl:template match="*" mode="emit-code">
        <xsl:param name="root"/>
        <xsl:param name="stack"/>
        <xsl:choose>
            <xsl:when test="self::lp5-">
                <xsl:call-template name="emit-reference">
                    <xsl:with-param name="root" select="$root"/>
                    <xsl:with-param name="name" select="normalize-space(@ref)"/>
                    <xsl:with-param name="stack" select="$stack"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy>
                    <xsl:apply-templates select="@*|node()" mode="emit-code">
                        <xsl:with-param name="root" select="$root"/>
                        <xsl:with-param name="stack" select="$stack"/>
                    </xsl:apply-templates>
                </xsl:copy>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="@*" mode="emit-code">
        <xsl:copy/>
    </xsl:template>

    <xsl:template name="emit-reference">
        <xsl:param name="root"/>
        <xsl:param name="name"/>
        <xsl:param name="stack"/>

        <xsl:if test="not(string-length($name))">
            <xsl:message terminate="yes">A code reference has no name.</xsl:message>
        </xsl:if>
        <xsl:if test="contains($stack, concat('|', $name, '|'))">
            <xsl:message terminate="yes">
                <xsl:text>Circular code reference: </xsl:text>
                <xsl:value-of select="$name"/>
            </xsl:message>
        </xsl:if>

        <xsl:variable name="matches">
            <xsl:call-template name="count-named-fragments">
                <xsl:with-param name="document" select="$root"/>
                <xsl:with-param name="name" select="$name"/>
            </xsl:call-template>
        </xsl:variable>
        <xsl:if test="not(string-length(string($matches)))">
            <xsl:message>
                <xsl:text>Skipping unresolved code fragment reference '</xsl:text>
                <xsl:value-of select="$name"/>
                <xsl:text>'.</xsl:text>
            </xsl:message>
        </xsl:if>

        <xsl:call-template name="emit-named-fragments">
            <xsl:with-param name="document" select="$root"/>
            <xsl:with-param name="root" select="$root"/>
            <xsl:with-param name="name" select="$name"/>
            <xsl:with-param name="stack" select="concat($stack, $name, '|')"/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="count-named-fragments">
        <xsl:param name="document"/>
        <xsl:param name="name"/>

        <xsl:for-each select="$document/template/section[@data-lp5-kind = 'code'][normalize-space(name) = $name]">
            <xsl:text>x</xsl:text>
        </xsl:for-each>
        <xsl:for-each select="$document/template/children/li">
            <xsl:variable name="child" select="document(string(@id), .)"/>
            <xsl:call-template name="count-named-fragments">
                <xsl:with-param name="document" select="$child"/>
                <xsl:with-param name="name" select="$name"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>

    <xsl:template name="emit-named-fragments">
        <xsl:param name="document"/>
        <xsl:param name="root"/>
        <xsl:param name="name"/>
        <xsl:param name="stack"/>

        <xsl:for-each select="$document/template/section[@data-lp5-kind = 'code'][normalize-space(name) = $name]/code">
            <xsl:apply-templates select="node()" mode="emit-code">
                <xsl:with-param name="root" select="$root"/>
                <xsl:with-param name="stack" select="$stack"/>
            </xsl:apply-templates>
        </xsl:for-each>
        <xsl:for-each select="$document/template/children/li">
            <xsl:variable name="child" select="document(string(@id), .)"/>
            <xsl:call-template name="emit-named-fragments">
                <xsl:with-param name="document" select="$child"/>
                <xsl:with-param name="root" select="$root"/>
                <xsl:with-param name="name" select="$name"/>
                <xsl:with-param name="stack" select="$stack"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>

</xsl:stylesheet>

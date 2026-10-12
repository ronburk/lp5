<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="tangle.xsl"/>
    <!-- Avoid inserting formatting whitespace into mixed content or code. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"
                omit-xml-declaration="no"/>

    <xsl:param name="article-file" select="'root.lp5'"/>

    <xsl:template match="/">
        <xsl:call-template name="validate-article">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="location" select="$article-file"/>
        </xsl:call-template>
        <lp5-article version="1" file="{$article-file}">
            <xsl:apply-templates select="template"/>
        </lp5-article>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

    <!-- Only code-section text is serialized as CDATA. Explanation markup,
         including inline <code>, must remain ordinary XML/HTML markup. -->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="section[@data-lp5-kind='code']/code">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()" mode="code"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="@*|node()" mode="code">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()" mode="code"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="text()" mode="code">
        <xsl:call-template name="emit-cdata">
            <xsl:with-param name="text" select="."/>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="emit-cdata">
        <xsl:param name="text"/>
        <xsl:text disable-output-escaping="yes">&lt;![CDATA[</xsl:text>
        <xsl:call-template name="emit-cdata-text">
            <xsl:with-param name="text" select="$text"/>
        </xsl:call-template>
        <xsl:text disable-output-escaping="yes">]]&gt;</xsl:text>
    </xsl:template>

    <!-- Keep generated CDATA well-formed when the source text contains ]]> . -->
    <xsl:template name="emit-cdata-text">
        <xsl:param name="text"/>
        <xsl:choose>
            <xsl:when test="contains($text, ']]&gt;')">
                <xsl:value-of select="substring-before($text, ']]&gt;')"
                              disable-output-escaping="yes"/>
                <xsl:text disable-output-escaping="yes">]]]]&gt;&lt;![CDATA[&gt;</xsl:text>
                <xsl:call-template name="emit-cdata-text">
                    <xsl:with-param name="text" select="substring-after($text, ']]&gt;')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$text" disable-output-escaping="yes"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
</xsl:stylesheet>

<?xml version="1.0" encoding="UTF-8"?>
<!--
     show-bundle.xsl - extract all code sections with one code name from a weave.

     Run this stylesheet on weave.xml, passing the required code_name string
     parameter and choosing the result filename with xsltproc's output option.

     The output contains only matching code sections, in article/weave order.
     Each definition retains its article filename and ordered code content.
     A references list records each lp5-* reference's target name and whether
     that target has a definition in the weave. Explanations are intentionally
     excluded. A bundle with no definitions is still returned with found="no".
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <!-- Avoid pretty-printing whitespace into copied code content. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <!-- A sentinel distinguishes an omitted required parameter from empty name. -->
    <xsl:param name="code_name" select="'__CODE_NAME_PARAMETER_REQUIRED__'"/>

    <xsl:template match="/">
        <xsl:if test="$code_name = '__CODE_NAME_PARAMETER_REQUIRED__'">
            <xsl:message terminate="yes">show-bundle.xsl requires --stringparam code_name NAME (use an empty value for the unnamed bundle).</xsl:message>
        </xsl:if>

        <xsl:variable name="canonical-name" select="normalize-space($code_name)"/>
        <xsl:variable name="definitions"
            select="/lp5-weave/articles/article/lp5-code[normalize-space(name) = $canonical-name]"/>

        <bundle name="{$canonical-name}">
            <xsl:attribute name="found">
                <xsl:choose>
                    <xsl:when test="$definitions">yes</xsl:when>
                    <xsl:otherwise>no</xsl:otherwise>
                </xsl:choose>
            </xsl:attribute>

            <xsl:for-each select="$definitions">
                <definition article="{../@file}">
                    <code>
                        <!-- Keep code nodes in source order, including references. -->
                        <xsl:copy-of select="code/node()"/>
                    </code>
                    <references>
                        <xsl:for-each select="code//*[starts-with(name(), 'lp5-')]">
                            <xsl:variable name="reference-name" select="normalize-space(@ref)"/>
                            <reference name="{$reference-name}">
                                <xsl:attribute name="defined">
                                    <xsl:choose>
                                        <xsl:when test="/lp5-weave/chunks/chunk[@name = $reference-name]">yes</xsl:when>
                                        <xsl:otherwise>no</xsl:otherwise>
                                    </xsl:choose>
                                </xsl:attribute>
                            </reference>
                        </xsl:for-each>
                    </references>
                </definition>
            </xsl:for-each>
        </bundle>
    </xsl:template>
</xsl:stylesheet>
